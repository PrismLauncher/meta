#!/bin/python3 

import os
import json
import copy
import datetime
import iso8601

from operator import itemgetter

from pprint import pprint

from metautil import GradleSpecifier, VersionPatch

def addOrGetBucket(buckets, rules):
    ruleHash = None
    if rules:
        ruleHash = hash(json.dumps(rules))

    bucket = None
    if ruleHash in buckets:
        bucket = buckets[ruleHash]
    else:
        bucket = VersionPatch("org.lwjgl", "LWJGL")
        bucket.releaseType = "release"
        buckets[ruleHash] = bucket
        bucket.rules = rules
    return bucket

def addLWJGLVersion(versions, bucket):
    if bucket.version in versions:
        if versions[bucket.version].rules:
            if not bucket.rules:
                versions[bucket.version].rules = None
        return
        if bucket.releaseTime < versions[bucket.version].releaseTime:
            versions[bucket.version].releaseTime = bucket.releaseTime
    versions[bucket.version] = bucket

lwjglVersions = {}
for filename in os.listdir('mojang/versions'):
    with open("mojang/versions/" + filename) as json_file:
        json_data = json.load(json_file)
        libs = json_data["libraries"]
        libs_minecraft = []
        buckets = {}
        for lib in libs:
            specifier = GradleSpecifier(lib["name"])
            ruleHash = None
            if specifier.isLwjgl():
                rules = None
                if "rules" in lib:
                    rules = lib["rules"]
                    lib.pop("rules", None)
                bucket = addOrGetBucket(buckets, rules)
                if specifier.group == "org.lwjgl.lwjgl" and specifier.artifact == "lwjgl":
                    bucket.version = specifier.version
                bucket.libraries.append(lib)
                # set the LWJGL release time to the oldest Minecraft release it appeared in
                if bucket.releaseTime == None:
                    bucket.releaseTime = iso8601.parse_date(json_data["releaseTime"])
                else:
                    newDate = iso8601.parse_date(json_data["releaseTime"])
                    if newDate < bucket.releaseTime:
                        bucket.releaseTime = newDate
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
        json_data["libraries"] = libs_minecraft
        json_data["name"] = "Minecraft"
        filenameOut = "multimc/net.minecraft/%s.json" % json_data["id"]
        with open(filenameOut, 'w') as outfile:
            json.dump(json_data, outfile, sort_keys=True, indent=4)

for version in lwjglVersions:
    versionObj = lwjglVersions[version]
    filename = "multimc/org.lwjgl/%s.json" % version
    versionObj.write(filename)
