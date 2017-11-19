#!/usr/bin/python3

import os
import json
import copy
import datetime
import iso8601

from operator import itemgetter

from pprint import pprint

from metautil import *

from distutils import version

def addOrGetBucket(buckets, rules):
    ruleHash = None
    if rules:
        ruleHash = hash(json.dumps(rules.to_json()))
        print("ruleHash for", rules, "is", ruleHash)

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

def adaptNewStyleArguments(arguments):
    outarr = []
    # we ignore the jvm arguments entirely.
    # grab the strings, log the complex stuff
    for arg in arguments.game:
        if isinstance(arg, str):
            outarr.append(arg)
        else:
            print("!!! Unrecognized structure in Minecraft game arguments:")
            pprint(arg)
    return ' '.join(outarr)

# get the local version list
staticVersionlist = None
with open("static/minecraft.json", 'r', encoding='utf-8') as legacyIndexFile:
    staticVersionlist = LegacyOverrideIndex(json.load(legacyIndexFile))

found_any_lwjgl3 = False
lwjglVersions = {}
for filename in os.listdir('upstream/mojang/versions'):
    with open("upstream/mojang/versions/" + filename) as json_file:
        print("Processing", filename)
        mojangVersionFile = MojangVersionFile(json.load(json_file))
        versionFile = MojangToMultiMC(mojangVersionFile, "Minecraft", "net.minecraft", mojangVersionFile.id)
        libs_minecraft = []
        is_lwjgl_3 = False
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
                if specifier.group == "org.lwjgl" and specifier.artifact == "lwjgl":
                    is_lwjgl_3 = True
                    found_any_lwjgl3 = True
                    bucket.version = specifier.version
                if not bucket.libraries:
                    bucket.libraries = []
                bucket.libraries.append(mmcLib)
                bucket.releaseTime = versionFile.releaseTime
            else:
                libs_minecraft.append(mmcLib)
        if len(buckets) == 1:
            addLWJGLVersion(lwjglVersions, buckets[None])
            print("Found only candidate LWJGL", buckets[None].version)
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
                print("Found candidate LWJGL", keyBucket.version, key)
        versionFile.libraries = libs_minecraft
        # TODO: add detection of LWJGL 3?
        if is_lwjgl_3:
            versionFile.requires = [DependencyEntry(uid='org.lwjgl3')]
        else:
            versionFile.requires = [DependencyEntry(uid='org.lwjgl')]
        versionFile.order = -2
        # process 1.13 arguments into previous version
        if not mojangVersionFile.minecraftArguments and mojangVersionFile.arguments:
            versionFile.minecraftArguments = adaptNewStyleArguments(mojangVersionFile.arguments)
        filenameOut = "multimc/net.minecraft/%s.json" % versionFile.version
        if versionFile.version in staticVersionlist.versions:
            ApplyLegacyOverride (versionFile, staticVersionlist.versions[versionFile.version])
        with open(filenameOut, 'w') as outfile:
            json.dump(versionFile.to_json(), outfile, sort_keys=True, indent=4)

for lwjglVersion in lwjglVersions:
    versionObj = lwjglVersions[lwjglVersion]
    if lwjglVersion[0] == '2':
        filename = "multimc/org.lwjgl/%s.json" % lwjglVersion
        versionObj.name = 'LWJGL 2'
        versionObj.uid = 'org.lwjgl'
        versionObj.conflicts = [DependencyEntry(uid='org.lwjgl3')]
    elif lwjglVersion[0] == '3':
        filename = "multimc/org.lwjgl3/%s.json" % lwjglVersion
        versionObj.name = 'LWJGL 3'
        versionObj.uid = 'org.lwjgl3'
        versionObj.conflicts = [DependencyEntry(uid='org.lwjgl')]
    else:
        raise Exception("LWJGL version not recognized: %s" % versionObj.version)

    versionObj.order = -1
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

lwjglSharedData = MultiMCSharedPackageData(uid = 'org.lwjgl', name = 'LWJGL 2')
lwjglSharedData.recommended = ['2.9.4-nightly-20150209']
lwjglSharedData.write()

if found_any_lwjgl3:
    lwjglSharedData = MultiMCSharedPackageData(uid = 'org.lwjgl3', name = 'LWJGL 3')
    lwjglSharedData.recommended = ['3.1.2']
    lwjglSharedData.write()

with open("upstream/mojang/version_manifest.json", 'r', encoding='utf-8') as localIndexFile:
    localVersionlist = MojangIndexWrap(json.load(localIndexFile))

mcSharedData = MultiMCSharedPackageData(uid = 'net.minecraft', name = 'Minecraft')
mcSharedData.recommended = [localVersionlist.latest['release']]
mcSharedData.write()