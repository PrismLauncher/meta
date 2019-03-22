#!/usr/bin/python3
'''
 Get the source files necessary for generating Forge versions
'''
from __future__ import print_function
import sys

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

import json
import copy
import re
import zipfile
from metautil import *
from jsonobject import *
from forgeutil import *
import os.path
import datetime
import hashlib
from pathlib import Path
from contextlib import suppress

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def filehash(filename, hashtype, blocksize=65536):
    hash = hashtype()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()

forever_cache = FileCache('http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)

# get the remote version list fragments
r = sess.get('https://files.minecraftforge.net/maven/net/minecraftforge/forge/maven-metadata.json')
r.raise_for_status()
main_json = r.json()
assert type(main_json) == dict

r = sess.get('https://files.minecraftforge.net/maven/net/minecraftforge/forge/promotions_slim.json')
r.raise_for_status()
promotions_json = r.json()
assert type(promotions_json) == dict

promotedKeyExpression = re.compile("((?P<mc>[0-9\\.]+)-)?(?P<promotion>(latest)|(recommended))(-(?P<branch>[a-zA-Z0-9\\.]+))?")

recommendedSet = set()

newIndex = NewForgeIndex()

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
        print ('%s added to recommended set' % shortversion)
    elif match.group('promotion') == 'latest':
        pass
    else:
        assert False

versionExpression = re.compile("^(?P<mc>[0-9a-zA-Z_\\.]+)-(?P<ver>[0-9\\.]+\\.(?P<build>[0-9]+))(-(?P<branch>[a-zA-Z0-9\\.]+))?$")

def getSingleForgeFilesManifest(longversion):
    pathThing = "upstream/forge/files_manifests/%s.json" % longversion
    files_manifest_file = Path(pathThing)
    from_file = False
    if files_manifest_file.is_file():
        with open(pathThing, 'r') as f:
            files_json=json.load(f)
            from_file = True
    else:
        fileUrl = 'https://files.minecraftforge.net/maven/net/minecraftforge/forge/%s/meta.json' % longversion
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
            assert type(classifier) == str
            assert type(hash) == str
            processedHash = re.sub(r"\W", "", hash)
            if not len(processedHash) == 32:
                print('%s: Skipping invalid hash for extension %s:' % (longversion, extension))
                pprint(extensionObj)
                index = index + 1
                continue

            fileObj = NewForgeFile(
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

        files = getSingleForgeFilesManifest(longversion)

        build = int(match.group('build'))
        version = match.group('ver')
        branch = match.group('branch')

        isRecommended = (version in recommendedSet)

        entry = NewForgeEntry(
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
            newIndex.by_mcversion.setdefault(mcversion, ForgeMcVersionInfo())
        newIndex.by_mcversion[mcversion].versions.append(longversion)
        # NOTE: we add this later after the fact. The forge promotions file lies about these.
        #if entry.latest:
            #newIndex.by_mcversion[mcversion].latest = longversion
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

with open("upstream/forge/maven-metadata.json", 'w', encoding='utf-8') as f:
    json.dump(main_json, f, sort_keys=True, indent=4)

with open("upstream/forge/promotions_slim.json", 'w', encoding='utf-8') as f:
    json.dump(promotions_json, f, sort_keys=True, indent=4)

with open("upstream/forge/derived_index.json", 'w', encoding='utf-8') as f:
    json.dump(newIndex.to_json(), f, sort_keys=True, indent=4)

versions = []
legacyinfolist = ForgeLegacyInfoList()
tsPath = "static/forge-legacyinfo.json"

print("Grabbing installers and dumping installer profiles...")
# get the installer jars - if needed - and get the installer profiles out of them
for id, entry in newIndex.versions.items():
    if entry.mcversion == None:
        eprint ("Skipping %d with invalid MC version" % entry.build)
        continue

    version = ForgeVersion2(entry)
    if version.url() == None:
        eprint ("Skipping %d with no valid files" % version.build)
        continue

    jarFilepath = "upstream/forge/jars/%s" % version.filename()

    if version.usesInstaller():
        profileFilepath = "upstream/forge/installer_manifests/%s.json" % version.longVersion
        versionJsonFilepath = "upstream/forge/version_manifests/%s.json" % version.longVersion
        if not os.path.isfile(profileFilepath):
            # grab the installer if it's not there
            if not os.path.isfile(jarFilepath):
                eprint ("Downloading %s" % version.url())
                rfile = sess.get(version.url(), stream=True)
                rfile.raise_for_status()
                with open(jarFilepath, 'wb') as f:
                    for chunk in rfile.iter_content(chunk_size=128):
                        f.write(chunk)
            print(jarFilepath)
            with zipfile.ZipFile(jarFilepath, 'r') as jar:
                with jar.open('install_profile.json', 'r') as profileZipEntry:
                    with open(profileFilepath, 'wb') as profileFile:
                        profileFile.write(profileZipEntry.read())
                        profileFile.close()
                    profileZipEntry.close()
                with suppress(KeyError):
                    with jar.open('version.json', 'r') as profileZipEntry:
                        with open(versionJsonFilepath, 'wb') as versionJsonFile:
                            versionJsonFile.write(profileZipEntry.read())
                            versionJsonFile.close()
                        profileZipEntry.close()
    else:
        pass
        # ignore the two versions without install manifests and jar mod class files
        # TODO: fix those versions?
        if version.mcversion_sane == "1.6.1":
            continue

        # only gather legacy info if it's missing
        if not os.path.isfile(tsPath):
            # grab the jar/zip if it's not there
            if not os.path.isfile(jarFilepath):
                rfile = sess.get(version.url(), stream=True)
                rfile.raise_for_status()
                with open(jarFilepath, 'wb') as f:
                    for chunk in rfile.iter_content(chunk_size=128):
                        f.write(chunk)
            # find the latest timestamp in the zip file
            tstamp =  datetime.datetime.fromtimestamp(0)
            with zipfile.ZipFile(jarFilepath, 'r') as jar:
                allinfo = jar.infolist()
                for info in allinfo:
                    tstampNew = datetime.datetime(*info.date_time)
                    if tstampNew > tstamp:
                        tstamp = tstampNew
            legacyInfo = ForgeLegacyInfo()
            legacyInfo.releaseTime = tstamp
            legacyInfo.sha1 = filehash(jarFilepath, hashlib.sha1)
            legacyInfo.sha256 = filehash(jarFilepath, hashlib.sha256)
            legacyInfo.size = os.path.getsize(jarFilepath)
            legacyinfolist.number[id] = legacyInfo

# only write legacy info if it's missing
if not os.path.isfile(tsPath):
    with open(tsPath, 'w') as outfile:
        json.dump(legacyinfolist.to_json(), outfile, sort_keys=True, indent=4)
