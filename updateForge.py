'''
 Get the source files necessary for generating Forge versions
'''
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

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
from pydantic import ValidationError

from meta.common import upstream_path, ensure_upstream_dir, static_path
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

forever_cache = FileCache('caches/http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def filehash(filename, hashtype, blocksize=65536):
    hash = hashtype()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()


def get_single_forge_files_manifest(longversion):
    print(f"Getting Forge manifest for {longversion}")
    pathThing = UPSTREAM_DIR + "/forge/files_manifests/%s.json" % longversion
    files_manifest_file = Path(pathThing)
    from_file = False
    if files_manifest_file.is_file():
        with open(pathThing, 'r') as f:
            files_json = json.load(f)
            from_file = True
    else:
        fileUrl = 'https://files.minecraftforge.net/net/minecraftforge/forge/%s/meta.json' % longversion
        r = sess.get(fileUrl)
        r.raise_for_status()
        files_json = r.json()

    retDict = dict()

    for classifier, extensionObj in files_json.get('classifiers').items():
        assert type(classifier) == str
        assert type(extensionObj) == dict

        # assert len(extensionObj.items()) == 1
        index = 0
        count = 0
        while index < len(extensionObj.items()):
            mutableCopy = copy.deepcopy(extensionObj)
            extension, hash = mutableCopy.popitem()
            if not type(classifier) == str:
                pprint(classifier)
                pprint(extensionObj)
            if not type(hash) == str:
                pprint(classifier)
                pprint(extensionObj)
                print('%s: Skipping missing hash for extension %s:' % (longversion, extension))
                index = index + 1
                continue
            assert type(classifier) == str
            processedHash = re.sub(r"\W", "", hash)
            if not len(processedHash) == 32:
                print('%s: Skipping invalid hash for extension %s:' % (longversion, extension))
                pprint(extensionObj)
                index = index + 1
                continue

            fileObj = ForgeFile(
                classifier=classifier,
                hash=processedHash,
                extension=extension
            )
            if count == 0:
                retDict[classifier] = fileObj
                index = index + 1
                count = count + 1
            else:
                print('%s: Multiple objects detected for classifier %s:' % (longversion, classifier))
                pprint(extensionObj)
                assert False

    if not from_file:
        with open(pathThing, 'w', encoding='utf-8') as f:
            json.dump(files_json, f, sort_keys=True, indent=4)

    return retDict


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

    promotedKeyExpression = re.compile(
        "(?P<mc>[^-]+)-(?P<promotion>(latest)|(recommended))(-(?P<branch>[a-zA-Z0-9\\.]+))?")

    recommendedSet = set()

    newIndex = DerivedForgeIndex()

    # FIXME: does not fully validate that the file has not changed format
    # NOTE: For some insane reason, the format of the versions here is special. It having a branch at the end means it affects that particular branch
    #       We don't care about Forge having branches.
    #       Therefore we only use the short version part for later identification and filter out the branch-specific promotions (among other errors).
    print("Processing promotions:")
    for promoKey, shortversion in promotions_json.get('promos').items():
        match = promotedKeyExpression.match(promoKey)
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
            recommendedSet.add(shortversion)
            print('%s added to recommended set' % shortversion)
        elif match.group('promotion') == 'latest':
            pass
        else:
            assert False

    versionExpression = re.compile(
        "^(?P<mc>[0-9a-zA-Z_\\.]+)-(?P<ver>[0-9\\.]+\\.(?P<build>[0-9]+))(-(?P<branch>[a-zA-Z0-9\\.]+))?$")

    print("")
    print("Processing versions:")
    for mcversion, value in main_json.items():
        assert type(mcversion) == str
        assert type(value) == list
        for longversion in value:
            assert type(longversion) == str
            match = versionExpression.match(longversion)
            if not match:
                pprint(longversion)
                assert match
            assert match.group('mc') == mcversion

            files = get_single_forge_files_manifest(longversion)

            build = int(match.group('build'))
            version = match.group('ver')
            branch = match.group('branch')

            isRecommended = (version in recommendedSet)

            entry = ForgeEntry(
                longversion=longversion,
                mcversion=mcversion,
                version=version,
                build=build,
                branch=branch,
                # NOTE: we add this later after the fact. The forge promotions file lies about these.
                latest=False,
                recommended=isRecommended,
                files=files
            )
            newIndex.versions[longversion] = entry
            if not newIndex.by_mcversion:
                newIndex.by_mcversion = dict()
            if not mcversion in newIndex.by_mcversion:
                newIndex.by_mcversion.setdefault(mcversion, ForgeMCVersionInfo())
            newIndex.by_mcversion[mcversion].versions.append(longversion)
            # NOTE: we add this later after the fact. The forge promotions file lies about these.
            # if entry.latest:
            # newIndex.by_mcversion[mcversion].latest = longversion
            if entry.recommended:
                newIndex.by_mcversion[mcversion].recommended = longversion

    print("")
    print("Post processing promotions and adding missing 'latest':")
    for mcversion, info in newIndex.by_mcversion.items():
        latestVersion = info.versions[-1]
        info.latest = latestVersion
        newIndex.versions[latestVersion].latest = True
        print("Added %s as latest for %s" % (latestVersion, mcversion))

    print("")
    print("Dumping index files...")

    with open(UPSTREAM_DIR + "/forge/maven-metadata.json", 'w', encoding='utf-8') as f:
        json.dump(main_json, f, sort_keys=True, indent=4)

    with open(UPSTREAM_DIR + "/forge/promotions_slim.json", 'w', encoding='utf-8') as f:
        json.dump(promotions_json, f, sort_keys=True, indent=4)

    newIndex.write(UPSTREAM_DIR + "/forge/derived_index.json")

    legacyinfolist = ForgeLegacyInfoList()

    print("Grabbing installers and dumping installer profiles...")
    # get the installer jars - if needed - and get the installer profiles out of them
    for id, entry in newIndex.versions.items():
        eprint("Updating Forge %s" % id)
        if entry.mcversion is None:
            eprint("Skipping %d with invalid MC version" % entry.build)
            continue

        version = ForgeVersion(entry)
        if version.url() is None:
            eprint("Skipping %d with no valid files" % version.build)
            continue
        if version.longVersion in BAD_VERSIONS:
            eprint(f"Skipping bad version {version.longVersion}")
            continue

        jarFilepath = UPSTREAM_DIR + "/forge/jars/%s" % version.filename()

        if version.uses_installer():
            installerInfoFilepath = UPSTREAM_DIR + "/forge/installer_info/%s.json" % version.longVersion
            profileFilepath = UPSTREAM_DIR + "/forge/installer_manifests/%s.json" % version.longVersion
            versionJsonFilepath = UPSTREAM_DIR + "/forge/version_manifests/%s.json" % version.longVersion
            installerRefreshRequired = False
            if not os.path.isfile(profileFilepath):
                installerRefreshRequired = True
            if not os.path.isfile(installerInfoFilepath):
                installerRefreshRequired = True

            if installerRefreshRequired:
                # grab the installer if it's not there
                if not os.path.isfile(jarFilepath):
                    eprint("Downloading %s" % version.url())
                    rfile = sess.get(version.url(), stream=True)
                    rfile.raise_for_status()
                    with open(jarFilepath, 'wb') as f:
                        for chunk in rfile.iter_content(chunk_size=128):
                            f.write(chunk)

            eprint("Processing %s" % version.url())
            # harvestables from the installer
            if not os.path.isfile(profileFilepath):
                print(jarFilepath)
                with zipfile.ZipFile(jarFilepath, 'r') as jar:
                    with suppress(KeyError):
                        with jar.open('version.json', 'r') as profileZipEntry:
                            versionJsonData = profileZipEntry.read()
                            profileZipEntry.close()

                            # Process: does it parse?
                            doesItParse = MojangVersion.parse_raw(versionJsonData)

                            with open(versionJsonFilepath, 'wb') as versionJsonFile:
                                versionJsonFile.write(versionJsonData)
                                versionJsonFile.close()

                    with jar.open('install_profile.json', 'r') as profileZipEntry:
                        installProfileJsonData = profileZipEntry.read()
                        profileZipEntry.close()

                        # Process: does it parse?
                        atLeastOneFormatWorked = False
                        exception = None
                        try:
                            ForgeInstallerProfile.parse_raw(installProfileJsonData)
                            atLeastOneFormatWorked = True
                        except ValidationError as err:
                            exception = err
                        try:
                            ForgeInstallerProfileV2.parse_raw(installProfileJsonData)
                            atLeastOneFormatWorked = True
                        except ValidationError as err:
                            exception = err

                        if not atLeastOneFormatWorked:
                            if version.is_supported():
                                raise exception
                            else:
                                eprint(
                                    "Version %s is not supported and won't be generated later." % version.longVersion)

                        with open(profileFilepath, 'wb') as profileFile:
                            profileFile.write(installProfileJsonData)
                            profileFile.close()

            # installer info v1
            if not os.path.isfile(installerInfoFilepath):
                installerInfo = InstallerInfo()
                installerInfo.sha1hash = filehash(jarFilepath, hashlib.sha1)
                installerInfo.sha256hash = filehash(jarFilepath, hashlib.sha256)
                installerInfo.size = os.path.getsize(jarFilepath)
                installerInfo.write(installerInfoFilepath)
        else:
            # ignore the two versions without install manifests and jar mod class files
            # TODO: fix those versions?
            if version.mcversion_sane == "1.6.1":
                continue

            # only gather legacy info if it's missing
            if not os.path.isfile(LEGACYINFO_PATH):
                # grab the jar/zip if it's not there
                if not os.path.isfile(jarFilepath):
                    rfile = sess.get(version.url(), stream=True)
                    rfile.raise_for_status()
                    with open(jarFilepath, 'wb') as f:
                        for chunk in rfile.iter_content(chunk_size=128):
                            f.write(chunk)
                # find the latest timestamp in the zip file
                tstamp = datetime.fromtimestamp(0)
                with zipfile.ZipFile(jarFilepath, 'r') as jar:
                    allinfo = jar.infolist()
                    for info in allinfo:
                        tstampNew = datetime(*info.date_time)
                        if tstampNew > tstamp:
                            tstamp = tstampNew
                legacyInfo = ForgeLegacyInfo()
                legacyInfo.releaseTime = tstamp
                legacyInfo.sha1 = filehash(jarFilepath, hashlib.sha1)
                legacyInfo.sha256 = filehash(jarFilepath, hashlib.sha256)
                legacyInfo.size = os.path.getsize(jarFilepath)
                legacyinfolist.number[id] = legacyInfo

    # only write legacy info if it's missing
    if not os.path.isfile(LEGACYINFO_PATH):
        legacyinfolist.write(LEGACYINFO_PATH)


if __name__ == '__main__':
    main()
