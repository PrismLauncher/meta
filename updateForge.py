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

from pydantic import ValidationError

from meta.common import upstream_path, ensure_upstream_dir, static_path, default_session
from meta.common.forge import JARS_DIR, INSTALLER_INFO_DIR, INSTALLER_MANIFEST_DIR, VERSION_MANIFEST_DIR, \
    FILE_MANIFEST_DIR, BAD_VERSIONS, STATIC_LEGACYINFO_FILE
from meta.model.forge import ForgeFile, ForgeEntry, ForgeMCVersionInfo, ForgeLegacyInfoList, DerivedForgeIndex, \
    ForgeVersion, ForgeInstallerProfile, ForgeInstallerProfileV2, InstallerInfo, \
    ForgeLegacyInfo
from meta.model.mojang import MojangVersion

UPSTREAM_DIR = upstream_path()
STATIC_DIR = static_path()

ensure_upstream_dir(JARS_DIR)
ensure_upstream_dir(INSTALLER_INFO_DIR)
ensure_upstream_dir(INSTALLER_MANIFEST_DIR)
ensure_upstream_dir(VERSION_MANIFEST_DIR)
ensure_upstream_dir(FILE_MANIFEST_DIR)

LEGACYINFO_PATH = os.path.join(STATIC_DIR, STATIC_LEGACYINFO_FILE)

sess = default_session()


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def filehash(filename, hashtype, blocksize=65536):
    hashtype = hashtype()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hashtype.update(block)
    return hashtype.hexdigest()


def get_single_forge_files_manifest(longversion):
    print(f"Getting Forge manifest for {longversion}")
    path_thing = UPSTREAM_DIR + "/forge/files_manifests/%s.json" % longversion
    files_manifest_file = Path(path_thing)
    from_file = False
    if files_manifest_file.is_file():
        with open(path_thing, 'r') as f:
            files_json = json.load(f)
            from_file = True
    else:
        file_url = 'https://files.minecraftforge.net/net/minecraftforge/forge/%s/meta.json' % longversion
        r = sess.get(file_url)
        r.raise_for_status()
        files_json = r.json()

    ret_dict = dict()

    for classifier, extensionObj in files_json.get('classifiers').items():
        assert type(classifier) == str
        assert type(extensionObj) == dict

        # assert len(extensionObj.items()) == 1
        index = 0
        count = 0
        while index < len(extensionObj.items()):
            mutable_copy = copy.deepcopy(extensionObj)
            extension, hashtype = mutable_copy.popitem()
            if not type(classifier) == str:
                pprint(classifier)
                pprint(extensionObj)
            if not type(hashtype) == str:
                pprint(classifier)
                pprint(extensionObj)
                print('%s: Skipping missing hash for extension %s:' % (longversion, extension))
                index += 1
                continue
            assert type(classifier) == str
            processed_hash = re.sub(r"\W", "", hashtype)
            if not len(processed_hash) == 32:
                print('%s: Skipping invalid hash for extension %s:' % (longversion, extension))
                pprint(extensionObj)
                index += 1
                continue

            file_obj = ForgeFile(
                classifier=classifier,
                hash=processed_hash,
                extension=extension
            )
            if count == 0:
                ret_dict[classifier] = file_obj
                index += 1
                count += 1
            else:
                print('%s: Multiple objects detected for classifier %s:' % (longversion, classifier))
                pprint(extensionObj)
                assert False

    if not from_file:
        with open(path_thing, 'w', encoding='utf-8') as f:
            json.dump(files_json, f, sort_keys=True, indent=4)

    return ret_dict


def main():
    # get the remote version list fragments
    r = sess.get('https://files.minecraftforge.net/net/minecraftforge/forge/maven-metadata.json')
    r.raise_for_status()
    main_json = r.json()
    assert type(main_json) == dict

    r = sess.get('https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json')
    r.raise_for_status()
    promotions_json = r.json()
    assert type(promotions_json) == dict

    promoted_key_expression = re.compile(
        "(?P<mc>[^-]+)-(?P<promotion>(latest)|(recommended))(-(?P<branch>[a-zA-Z0-9\\.]+))?")

    recommended_set = set()

    new_index = DerivedForgeIndex()

    # FIXME: does not fully validate that the file has not changed format
    # NOTE: For some insane reason, the format of the versions here is special. It having a branch at the end means it
    #           affects that particular branch.
    #       We don't care about Forge having branches.
    #       Therefore we only use the short version part for later identification and filter out the branch-specific
    #           promotions (among other errors).
    print("Processing promotions:")
    for promoKey, shortversion in promotions_json.get('promos').items():
        match = promoted_key_expression.match(promoKey)
        if not match:
            print('Skipping promotion %s, the key did not parse:' % promoKey)
            pprint(promoKey)
            assert match
        if not match.group('mc'):
            print('Skipping promotion %s, because it has no Minecraft version.' % promoKey)
            continue
        if match.group('branch'):
            print('Skipping promotion %s, because it on a branch only.' % promoKey)
            continue
        elif match.group('promotion') == 'recommended':
            recommended_set.add(shortversion)
            print('%s added to recommended set' % shortversion)
        elif match.group('promotion') == 'latest':
            pass
        else:
            assert False

    version_expression = re.compile(
        "^(?P<mc>[0-9a-zA-Z_\\.]+)-(?P<ver>[0-9\\.]+\\.(?P<build>[0-9]+))(-(?P<branch>[a-zA-Z0-9\\.]+))?$")

    print("")
    print("Processing versions:")
    for mc_version, value in main_json.items():
        assert type(mc_version) == str
        assert type(value) == list
        for long_version in value:
            assert type(long_version) == str
            match = version_expression.match(long_version)
            if not match:
                pprint(long_version)
                assert match
            assert match.group('mc') == mc_version

            files = get_single_forge_files_manifest(long_version)

            build = int(match.group('build'))
            version = match.group('ver')
            branch = match.group('branch')

            is_recommended = (version in recommended_set)

            entry = ForgeEntry(
                long_version=long_version,
                mc_version=mc_version,
                version=version,
                build=build,
                branch=branch,
                # NOTE: we add this later after the fact. The forge promotions file lies about these.
                latest=False,
                recommended=is_recommended,
                files=files
            )
            new_index.versions[long_version] = entry
            if not new_index.by_mc_version:
                new_index.by_mc_version = dict()
            if mc_version not in new_index.by_mc_version:
                new_index.by_mc_version.setdefault(mc_version, ForgeMCVersionInfo())
            new_index.by_mc_version[mc_version].versions.append(long_version)
            # NOTE: we add this later after the fact. The forge promotions file lies about these.
            # if entry.latest:
            # new_index.by_mc_version[mc_version].latest = long_version
            if entry.recommended:
                new_index.by_mc_version[mc_version].recommended = long_version

    print("")
    print("Post processing promotions and adding missing 'latest':")
    for mc_version, info in new_index.by_mc_version.items():
        latest_version = info.versions[-1]
        info.latest = latest_version
        new_index.versions[latest_version].latest = True
        print("Added %s as latest for %s" % (latest_version, mc_version))

    print("")
    print("Dumping index files...")

    with open(UPSTREAM_DIR + "/forge/maven-metadata.json", 'w', encoding='utf-8') as f:
        json.dump(main_json, f, sort_keys=True, indent=4)

    with open(UPSTREAM_DIR + "/forge/promotions_slim.json", 'w', encoding='utf-8') as f:
        json.dump(promotions_json, f, sort_keys=True, indent=4)

    new_index.write(UPSTREAM_DIR + "/forge/derived_index.json")

    legacy_info_list = ForgeLegacyInfoList()

    print("Grabbing installers and dumping installer profiles...")
    # get the installer jars - if needed - and get the installer profiles out of them
    for key, entry in new_index.versions.items():
        eprint("Updating Forge %s" % key)
        if entry.mc_version is None:
            eprint("Skipping %d with invalid MC version" % entry.build)
            continue

        version = ForgeVersion(entry)
        if version.url() is None:
            eprint("Skipping %d with no valid files" % version.build)
            continue
        if version.long_version in BAD_VERSIONS:
            eprint(f"Skipping bad version {version.long_version}")
            continue

        jar_path = os.path.join(UPSTREAM_DIR, JARS_DIR, version.filename())

        if version.uses_installer():
            installer_info_path = UPSTREAM_DIR + "/forge/installer_info/%s.json" % version.long_version
            profile_path = UPSTREAM_DIR + "/forge/installer_manifests/%s.json" % version.long_version
            version_file_path = UPSTREAM_DIR + "/forge/version_manifests/%s.json" % version.long_version

            installer_refresh_required = not os.path.isfile(profile_path) or not os.path.isfile(installer_info_path)

            if installer_refresh_required:
                # grab the installer if it's not there
                if not os.path.isfile(jar_path):
                    eprint("Downloading %s" % version.url())
                    rfile = sess.get(version.url(), stream=True)
                    rfile.raise_for_status()
                    with open(jar_path, 'wb') as f:
                        for chunk in rfile.iter_content(chunk_size=128):
                            f.write(chunk)

            eprint("Processing %s" % version.url())
            # harvestables from the installer
            if not os.path.isfile(profile_path):
                print(jar_path)
                with zipfile.ZipFile(jar_path) as jar:
                    with suppress(KeyError):
                        with jar.open('version.json') as profile_zip_entry:
                            version_data = profile_zip_entry.read()

                            # Process: does it parse?
                            MojangVersion.parse_raw(version_data)

                            with open(version_file_path, 'wb') as versionJsonFile:
                                versionJsonFile.write(version_data)
                                versionJsonFile.close()

                    with jar.open('install_profile.json') as profile_zip_entry:
                        install_profile_data = profile_zip_entry.read()

                        # Process: does it parse?
                        is_parsable = False
                        exception = None
                        try:
                            ForgeInstallerProfile.parse_raw(install_profile_data)
                            is_parsable = True
                        except ValidationError as err:
                            exception = err
                        try:
                            ForgeInstallerProfileV2.parse_raw(install_profile_data)
                            is_parsable = True
                        except ValidationError as err:
                            exception = err

                        if not is_parsable:
                            if version.is_supported():
                                raise exception
                            else:
                                eprint(
                                    "Version %s is not supported and won't be generated later." % version.long_version)

                        with open(profile_path, 'wb') as profileFile:
                            profileFile.write(install_profile_data)
                            profileFile.close()

            # installer info v1
            if not os.path.isfile(installer_info_path):
                installer_info = InstallerInfo()
                installer_info.sha1hash = filehash(jar_path, hashlib.sha1)
                installer_info.sha256hash = filehash(jar_path, hashlib.sha256)
                installer_info.size = os.path.getsize(jar_path)
                installer_info.write(installer_info_path)
        else:
            # ignore the two versions without install manifests and jar mod class files
            # TODO: fix those versions?
            if version.mc_version_sane == "1.6.1":
                continue

            # only gather legacy info if it's missing
            if not os.path.isfile(LEGACYINFO_PATH):
                # grab the jar/zip if it's not there
                if not os.path.isfile(jar_path):
                    rfile = sess.get(version.url(), stream=True)
                    rfile.raise_for_status()
                    with open(jar_path, 'wb') as f:
                        for chunk in rfile.iter_content(chunk_size=128):
                            f.write(chunk)
                # find the latest timestamp in the zip file
                tstamp = datetime.fromtimestamp(0)
                with zipfile.ZipFile(jar_path) as jar:
                    for info in jar.infolist():
                        tstamp_new = datetime(*info.date_time)
                        if tstamp_new > tstamp:
                            tstamp = tstamp_new
                legacy_info = ForgeLegacyInfo()
                legacy_info.release_time = tstamp
                legacy_info.sha1 = filehash(jar_path, hashlib.sha1)
                legacy_info.sha256 = filehash(jar_path, hashlib.sha256)
                legacy_info.size = os.path.getsize(jar_path)
                legacy_info_list.number[key] = legacy_info

    # only write legacy info if it's missing
    if not os.path.isfile(LEGACYINFO_PATH):
        legacy_info_list.write(LEGACYINFO_PATH)


if __name__ == '__main__':
    main()
