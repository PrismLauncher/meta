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

# get the local version list
staticVersionlist = None
with open("static/minecraft.json", 'r', encoding='utf-8') as legacyIndexFile:
    staticVersionlist = LegacyOverrideIndex(json.load(legacyIndexFile))

lwjglVersions = {}
for filename in os.listdir('mojang/versions'):
    with open("mojang/versions/" + filename) as json_file:
        mojangVersionFile = MojangVersionFile(json.load(json_file))
        versionFile = MojangToMultiMC(mojangVersionFile, "Minecraft", "net.minecraft", mojangVersionFile.id)
        libs_minecraft = []
        buckets = {}
        for lib in versionFile.libraries:
            libCopy = copy.deepcopy(lib)
            specifier = libCopy.name
            ruleHash = None
            if specifier.isLwjgl():
                rules = None
                if libCopy.rules:
                    rules = libCopy.rules
                    libCopy.rules = None
                bucket = addOrGetBucket(buckets, rules)
                if specifier.group == "org.lwjgl.lwjgl" and specifier.artifact == "lwjgl":
                    bucket.version = specifier.version
                if not bucket.libraries:
                    bucket.libraries = []
                bucket.libraries.append(libCopy)
                bucket.releaseTime = versionFile.releaseTime
            else:
                libs_minecraft.append(lib)
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
        versionFile.id = mojangVersionFile.id
        filenameOut = "multimc/net.minecraft/%s.json" % versionFile.version
        if versionFile.version in staticVersionlist.versions:
            ApplyLegacyOverride (versionFile, staticVersionlist.versions[versionFile.version])
        with open(filenameOut, 'w') as outfile:
            json.dump(versionFile.to_json(), outfile, sort_keys=True, indent=4)

for version in lwjglVersions:
    versionObj = lwjglVersions[version]
    filename = "multimc/org.lwjgl/%s.json" % version
    with open(filename, 'w') as outfile:
        json.dump(versionObj.to_json(), outfile, sort_keys=True, indent=4)
