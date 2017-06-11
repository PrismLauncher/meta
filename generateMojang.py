#!/bin/python3 

import os
import json
import copy
import datetime
import iso8601

from operator import itemgetter

from pprint import pprint

from metautil import *

def addOrGetBucket(buckets, rules):
    ruleHash = None
    if rules:
        ruleHash = hash(json.dumps(rules.to_json()))

    bucket = None
    if ruleHash in buckets:
        bucket = buckets[ruleHash]
    else:
        bucket = MultiMCVersionFile(
            {
                "name": "LWJGL",
                "version": "undetermined",
                "uid": "org.lwjgl"
            }
        )
        bucket.type = "release"
        buckets[ruleHash] = bucket
    return bucket

def addLWJGLVersion(versions, bucket):
    if bucket.version in versions:
        if bucket.releaseTime < versions[bucket.version].releaseTime:
            versions[bucket.version].releaseTime = bucket.releaseTime
    else:
        versions[bucket.version] = bucket

def removePathsFromLib(lib):
    if mmcLib.downloads.artifact:
        mmcLib.downloads.artifact.path = None
    if mmcLib.downloads.classifiers:
        for key, value in mmcLib.downloads.classifiers.items():
            value.path = None

# get the local version list
staticVersionlist = None
with open("static/minecraft.json", 'r', encoding='utf-8') as legacyIndexFile:
    staticVersionlist = LegacyOverrideIndex(json.load(legacyIndexFile))

lwjglVersions = {}
for filename in os.listdir('upstream/mojang/versions'):
    with open("upstream/mojang/versions/" + filename) as json_file:
        mojangVersionFile = MojangVersionFile(json.load(json_file))
        versionFile = MojangToMultiMC(mojangVersionFile, "Minecraft", "net.minecraft", mojangVersionFile.id)
        libs_minecraft = []
        buckets = {}
        for lib in versionFile.libraries:
            mmcLib = MultiMCLibrary(lib.to_json())
            removePathsFromLib(mmcLib)
            specifier = mmcLib.name
            ruleHash = None
            # ignore the mojang netty hack that prevents connection to select servers they don't like
            if specifier.isMojangNetty():
                print("Ignoring Mojang netty hack in version", versionFile.version)
                continue
            if specifier.isLwjgl():
                rules = None
                if mmcLib.rules:
                    rules = mmcLib.rules
                    mmcLib.rules = None
                bucket = addOrGetBucket(buckets, rules)
                if specifier.group == "org.lwjgl.lwjgl" and specifier.artifact == "lwjgl":
                    bucket.version = specifier.version
                if not bucket.libraries:
                    bucket.libraries = []
                bucket.libraries.append(mmcLib)
                bucket.releaseTime = versionFile.releaseTime
            else:
                libs_minecraft.append(mmcLib)
        if len(buckets) == 1:
            addLWJGLVersion(lwjglVersions, buckets[None])
        else:
            for key in buckets:
                if key == None:
                    continue
                keyBucket = buckets[key]
                if None in buckets:
                    keyBucket.libraries = sorted(keyBucket.libraries + buckets[None].libraries, key=itemgetter('name'))
                else:
                    keyBucket.libraries = sorted(keyBucket.libraries, key=itemgetter('name'))
                addLWJGLVersion(lwjglVersions, keyBucket)
        versionFile.libraries = libs_minecraft
        # TODO: add detection of LWJGL 3?
        versionFile.requires = {'org.lwjgl': '2.*'}
        versionFile.order = -2
        filenameOut = "multimc/net.minecraft/%s.json" % versionFile.version
        if versionFile.version in staticVersionlist.versions:
            ApplyLegacyOverride (versionFile, staticVersionlist.versions[versionFile.version])
        with open(filenameOut, 'w') as outfile:
            json.dump(versionFile.to_json(), outfile, sort_keys=True, indent=4)

for version in lwjglVersions:
    versionObj = lwjglVersions[version]
    versionObj.order = -1
    filename = "multimc/org.lwjgl/%s.json" % version
    good = True
    for lib in versionObj.libraries:
        if not lib.natives:
            continue
        checkedDict = {'linux', 'windows', 'osx'}
        if not checkedDict.issubset(lib.natives.keys()):
            print("Missing system classifier!", versionObj.version, lib.name, lib.natives.keys())
            good = False
            break
        if lib.downloads:
            for entry in checkedDict:
                bakedEntry = lib.natives[entry]
                if not bakedEntry in lib.downloads.classifiers:
                    print("Missing download for classifier!", versionObj.version, lib.name, bakedEntry, lib.downloads.classifiers.keys())
                    good = False
                    break
    if good:
        with open(filename, 'w') as outfile:
            json.dump(versionObj.to_json(), outfile, sort_keys=True, indent=4)
    else:
        print("Skipped LWJGL", versionObj.version)

lwjglSharedData = MultiMCSharedPackageData(uid = 'org.lwjgl', name = 'LWJGL')
lwjglSharedData.recommended = ['2.9.4-nightly-20150209']
lwjglSharedData.write()

with open("upstream/mojang/version_manifest.json", 'r', encoding='utf-8') as localIndexFile:
    localVersionlist = MojangIndexWrap(json.load(localIndexFile))

mcSharedData = MultiMCSharedPackageData(uid = 'net.minecraft', name = 'Minecraft')
mcSharedData.recommended = [localVersionlist.latest['release']]
mcSharedData.write()
