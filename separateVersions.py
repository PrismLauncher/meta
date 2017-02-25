#!/bin/python3 

import os
import json
import copy
from operator import itemgetter

from pprint import pprint

class GradleSpecifier:
    'A gradle specifier - a maven coordinate'

    def __init__(self, name):
        components = name.split(':')
        self.group = components[0]
        self.artifact = components[1]
        self.version = components[2]
        if len(components) == 4:
            self.classifier = components[3]
        else:
            self.classifier = None
   
    def toString(self):
        if self.classifier:
            return "%s:%s:%s:%s" % (self.group, self.artifact, self.version, self.classifier)
        else:
            return "%s:%s:%s" % (self.group, self.artifact, self.version)

def isLwjgl(specifier):
    return specifier.group in ("org.lwjgl.lwjgl", "net.java.jinput", "net.java.jutils")

class LwjglBucket:
    'A bucket for collecting LWJGL information'

    def __init__(self, hashkey):
        self.hashkey = hashkey
        self.libraries = []
        self.version = None
        self.rules = []

    def printout(self):
        if self.hashkey:
            print ("HashKey: %d" % self.hashkey)
        if self.version:
            print ("Version: " + self.version)
        print ("Libraries:")
        pprint(self.libraries)
        print ("Rules:")
        pprint(self.rules)

    def write(self, filename):
        out = {}
        out["libraries"] = self.libraries
        out["rules"] = self.rules
        out["version"] = self.version
        out["fileId"] = "org.lwjgl"
        out["name"] = "LWJGL"
        out["type"] = "release"
        out["releaseTime"] = "LWJGL"
        with open(filename, 'w') as outfile:
            json.dump(out, outfile, sort_keys=True, indent=4)

def addOrGetBucket(buckets, rules):
    ruleHash = None
    if rules:
        ruleHash = hash(json.dumps(rules))

    bucket = None
    if ruleHash in buckets:
        bucket = buckets[ruleHash]
    else:
        bucket = LwjglBucket(ruleHash)
        buckets[ruleHash] = bucket
        bucket.rules = rules
    return bucket

def addLWJGLVersion(versions, bucket):
    if bucket.version in versions:
        if versions[bucket.version].rules:
            if not bucket.rules:
                versions[bucket.version].rules = None
        return
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
            if isLwjgl(specifier):
                rules = None
                if "rules" in lib:
                    rules = lib["rules"]
                    lib.pop("rules", None)
                bucket = addOrGetBucket(buckets, rules)
                if specifier.group == "org.lwjgl.lwjgl" and specifier.artifact == "lwjgl":
                    bucket.version = specifier.version
                bucket.libraries.append(lib)
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
