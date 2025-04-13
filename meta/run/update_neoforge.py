"""
 Get the source files necessary for generating Forge versions
"""

import copy
import hashlib
import json
import os
import re
import sys
import zipfile
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from pprint import pprint
import urllib.parse

from pydantic import ValidationError

from meta.common import upstream_path, ensure_upstream_dir, default_session
from meta.common.neoforge import (
    JARS_DIR,
    INSTALLER_INFO_DIR,
    INSTALLER_MANIFEST_DIR,
    VERSION_MANIFEST_DIR,
    FILE_MANIFEST_DIR,
)
from meta.model.neoforge import (
    NeoForgeFile,
    NeoForgeEntry,
    NeoForgeMCVersionInfo,
    DerivedNeoForgeIndex,
    NeoForgeVersion,
    NeoForgeInstallerProfileV2,
    InstallerInfo,
)
from meta.model.mojang import MojangVersion

UPSTREAM_DIR = upstream_path()

ensure_upstream_dir(JARS_DIR)
ensure_upstream_dir(INSTALLER_INFO_DIR)
ensure_upstream_dir(INSTALLER_MANIFEST_DIR)
ensure_upstream_dir(VERSION_MANIFEST_DIR)
ensure_upstream_dir(FILE_MANIFEST_DIR)

sess = default_session()


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def filehash(filename, hashtype, blocksize=65536):
    hashtype = hashtype()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hashtype.update(block)
    return hashtype.hexdigest()


def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start + len(needle))
        n -= 1
    return start


def get_single_forge_files_manifest(longversion, artifact: str):
    print(f"Getting NeoForge manifest for {longversion}")
    path_thing = UPSTREAM_DIR + "/neoforge/files_manifests/%s.json" % longversion
    files_manifest_file = Path(path_thing)
    from_file = False
    if files_manifest_file.is_file():
        with open(path_thing, "r") as f:
            files_json = json.load(f)
            from_file = True
    else:
        file_url = (
            f"https://maven.neoforged.net/api/maven/details/releases/net%2Fneoforged%2F{artifact}%2F"
            + urllib.parse.quote(longversion)
        )
        r = sess.get(file_url)
        r.raise_for_status()
        files_json = r.json()

    ret_dict = dict()

    for file in files_json.get("files"):
        assert type(file) == dict
        name = file["name"]
        prefix = f"{artifact}-{longversion}"
        assert name.startswith(
            prefix
        ), f"{longversion} classifier {name} doesn't start with {prefix}"
        file_name = name[len(prefix) :]
        if file_name.startswith("-"):
            file_name = file_name[1:]
        if file_name.startswith("."):
            continue

        classifier, ext = os.path.splitext(file_name)

        if ext in [".md5", ".sha1", ".sha256", ".sha512"]:
            continue

        # assert len(extensionObj.items()) == 1
        file_obj = NeoForgeFile(
            artifact=artifact, classifier=classifier, extension=ext[1:]
        )
        ret_dict[classifier] = file_obj

    if not from_file:
        Path(path_thing).parent.mkdir(parents=True, exist_ok=True)
        with open(path_thing, "w", encoding="utf-8") as f:
            json.dump(files_json, f, sort_keys=True, indent=4)

    return ret_dict


def main():
    # get the remote version list fragments
    r = sess.get(
        "https://maven.neoforged.net/api/maven/versions/releases/net%2Fneoforged%2Fforge"
    )
    r.raise_for_status()
    main_json = r.json()["versions"]
    assert type(main_json) == list

    # get the new remote version list fragments
    r = sess.get(
        "https://maven.neoforged.net/api/maven/versions/releases/net%2Fneoforged%2Fneoforge"
    )
    r.raise_for_status()
    new_main_json = r.json()["versions"]
    assert type(new_main_json) == list

    main_json += new_main_json

    new_index = DerivedNeoForgeIndex()

    version_expression = re.compile(
        r"^(?P<mc>[0-9a-zA-Z_\.]+)-(?P<ver>[0-9\.]+\.(?P<build>[0-9]+))(-(?P<branch>[a-zA-Z0-9\.]+))?$"
    )
    neoforge_version_re = re.compile(
        r"^(?P<mcminor>\d+).(?:(?P<mcpatch>\d+)|(?P<snapshot>[0-9a-z]+)).(?P<number>\d+)(?:-(?P<tag>\w+))?$"
    )

    print("")
    print("Processing versions:")
    for long_version in main_json:
        assert type(long_version) == str

        match = version_expression.match(long_version)
        if match:
            mc_version = match.group("mc")
            build = int(match.group("build"))
            version = match.group("ver")
            branch = match.group("branch")
            artifact = "forge"

        match_nf = neoforge_version_re.match(long_version)
        if match_nf:
            mc_version = match_nf.group("snapshot")
            if not mc_version:
                mc_version = f"1.{match_nf.group('mcminor')}"
                if match_nf.group("mcpatch") != "0":
                    mc_version += f".{match_nf.group('mcpatch')}"
            build = int(match_nf.group("number"))
            version = match_nf.group("number")
            branch = match_nf.group("tag")
            match = match_nf
            artifact = "neoforge"

        assert match, f"{long_version} doesn't match version regex"
        try:
            files = get_single_forge_files_manifest(long_version, artifact)
        except:
            continue

        # TODO: what *is* recommended?
        is_recommended = False

        entry = NeoForgeEntry(
            artifact=artifact,
            long_version=long_version,
            mc_version=mc_version,
            version=version,
            build=build,
            branch=branch,
            # NOTE: we add this later after the fact. The forge promotions file lies about these.
            latest=False,
            recommended=is_recommended,
            files=files,
        )
        new_index.versions[long_version] = entry
        if not new_index.by_mc_version:
            new_index.by_mc_version = dict()
        if mc_version not in new_index.by_mc_version:
            new_index.by_mc_version.setdefault(mc_version, NeoForgeMCVersionInfo())
        new_index.by_mc_version[mc_version].versions.append(long_version)
        # NOTE: we add this later after the fact. The forge promotions file lies about these.
        # if entry.latest:
        # new_index.by_mc_version[mc_version].latest = long_version
        if entry.recommended:
            new_index.by_mc_version[mc_version].recommended = long_version

    print("")
    print("Dumping index files...")

    with open(
        UPSTREAM_DIR + "/neoforge/maven-metadata.json", "w", encoding="utf-8"
    ) as f:
        json.dump(main_json, f, sort_keys=True, indent=4)

    new_index.write(UPSTREAM_DIR + "/neoforge/derived_index.json")

    print("Grabbing installers and dumping installer profiles...")
    # get the installer jars - if needed - and get the installer profiles out of them
    for key, entry in new_index.versions.items():
        eprint("Updating NeoForge %s" % key)
        if entry.mc_version is None:
            eprint("Skipping %d with invalid MC version" % entry.build)
            continue

        version = NeoForgeVersion(entry)
        if version.url() is None:
            eprint("Skipping %d with no valid files" % version.build)
            continue
        if not version.uses_installer():
            eprint(f"version {version.long_version} does not use installer")
            continue

        jar_path = os.path.join(UPSTREAM_DIR, JARS_DIR, version.filename())

        installer_info_path = (
            UPSTREAM_DIR + "/neoforge/installer_info/%s.json" % version.long_version
        )
        profile_path = (
            UPSTREAM_DIR
            + "/neoforge/installer_manifests/%s.json" % version.long_version
        )
        version_file_path = (
            UPSTREAM_DIR + "/neoforge/version_manifests/%s.json" % version.long_version
        )

        installer_refresh_required = not os.path.isfile(
            profile_path
        ) or not os.path.isfile(installer_info_path)

        if installer_refresh_required:
            # grab the installer if it's not there
            if not os.path.isfile(jar_path):
                eprint("Downloading %s" % version.url())
                try:
                    rfile = sess.get(version.url(), stream=True)
                    rfile.raise_for_status()
                    Path(jar_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(jar_path, "wb") as f:
                        for chunk in rfile.iter_content(chunk_size=128):
                            f.write(chunk)
                except Exception as e:
                    eprint("Failed to download %s" % version.url())
                    eprint("Error is %s" % e)
                    continue

        eprint("Processing %s" % version.url())
        # harvestables from the installer
        if not os.path.isfile(profile_path):
            print(jar_path)
            with zipfile.ZipFile(jar_path) as jar:
                with suppress(KeyError):
                    with jar.open("version.json") as profile_zip_entry:
                        version_data = profile_zip_entry.read()

                        # Process: does it parse?
                        MojangVersion.parse_raw(version_data)

                        Path(version_file_path).parent.mkdir(
                            parents=True, exist_ok=True
                        )
                        with open(version_file_path, "wb") as versionJsonFile:
                            versionJsonFile.write(version_data)
                            versionJsonFile.close()

                with jar.open("install_profile.json") as profile_zip_entry:
                    install_profile_data = profile_zip_entry.read()

                    # Process: does it parse?
                    is_parsable = False
                    exception = None
                    try:
                        NeoForgeInstallerProfileV2.parse_raw(install_profile_data)
                        is_parsable = True
                    except ValidationError as err:
                        exception = err

                    if not is_parsable:
                        if version.is_supported():
                            raise exception
                        else:
                            eprint(
                                "Version %s is not supported and won't be generated later."
                                % version.long_version
                            )

                    Path(profile_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(profile_path, "wb") as profileFile:
                        profileFile.write(install_profile_data)
                        profileFile.close()

        # installer info v1
        if not os.path.isfile(installer_info_path):
            installer_info = InstallerInfo()
            installer_info.sha1hash = filehash(jar_path, hashlib.sha1)
            installer_info.sha256hash = filehash(jar_path, hashlib.sha256)
            installer_info.size = os.path.getsize(jar_path)
            installer_info.write(installer_info_path)


if __name__ == "__main__":
    main()
