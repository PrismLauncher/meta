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

from collections import defaultdict
from collections import namedtuple
from datetime import datetime
import hashlib

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

def hashVersion(lwjgl):
    lwjglObjectCopy = copy.deepcopy(lwjgl)
    lwjglObjectCopy.releaseTime = datetime.fromtimestamp(0)
    return hashlib.sha1(json.dumps(lwjglObjectCopy.to_json()).encode("utf-8", "strict")).hexdigest()

def sort_libs_by_name(library):
    return library.name

LWJGLEntry = namedtuple('LWJGLEntry', ('version', 'sha1'))

lwjglVersionVariants = defaultdict(list)

def addLWJGLVersion(versionVariants, lwjglObject):
    lwjglObjectCopy = copy.deepcopy(lwjglObject)
    libraries = list(lwjglObjectCopy.libraries)
    libraries.sort(key=sort_libs_by_name)
    lwjglObjectCopy.libraries = libraries

    lwjglVersion = lwjglObjectCopy.version
    lwjglObjectHash = hashVersion(lwjglObjectCopy)
    found = False
    for variant in versionVariants[lwjglVersion]:
        existingHash = variant.sha1
        if lwjglObjectHash == existingHash:
            found = True
            break
    if not found:
        print("!!! New variant for LWJGL version %s" % (lwjglVersion))
        versionVariants[lwjglVersion].append(LWJGLEntry(version=lwjglObjectCopy, sha1=lwjglObjectHash))

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

def isOnlyMacOS(rules, specifier):
    allowsOSX = False
    allowsAll = False
    #print("Considering", specifier, "rules", rules)
    if rules:
        for rule in rules:
            if rule.action == "allow" and rule.os and rule.os.name == "osx":
                allowsOSX = True
            if rule.action == "allow" and not rule.os:
                allowsAll = True
        if allowsOSX and not allowsAll:
            return True
    return False


# get the local version list
staticVersionlist = None
with open("static/minecraft.json", 'r', encoding='utf-8') as legacyIndexFile:
    staticVersionlist = LegacyOverrideIndex(json.load(legacyIndexFile))

found_any_lwjgl3 = False

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
            if specifier.isLwjgl():
                rules = None
                if mmcLib.rules:
                    rules = mmcLib.rules
                    mmcLib.rules = None
                if isOnlyMacOS(rules, specifier):
                    continue
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
            addLWJGLVersion(lwjglVersionVariants, buckets[None])
            print("Found only candidate LWJGL", buckets[None].version)
        else:
            # multiple buckets for LWJGL. [None] is common to all, other keys are for different sets of rules
            for key in buckets:
                if key == None:
                    continue
                keyBucket = buckets[key]
                if None in buckets:
                    keyBucket.libraries = sorted(keyBucket.libraries + buckets[None].libraries, key=itemgetter('name'))
                else:
                    keyBucket.libraries = sorted(keyBucket.libraries, key=itemgetter('name'))
                addLWJGLVersion(lwjglVersionVariants, keyBucket)
                print("Found candidate LWJGL", keyBucket.version, key)
            # remove the common bucket...
            if None in buckets:
                del buckets[None]
        versionFile.libraries = libs_minecraft
        depentry = None

        if is_lwjgl_3:
            depentry = DependencyEntry(uid='org.lwjgl3')
        else:
            depentry = DependencyEntry(uid='org.lwjgl')
        if len(buckets) == 1:
            suggestedVersion = next(iter(buckets.values())).version
            # HACK: forcing hard dependencies here for now... the UI doesn't know how to filter by this and it looks odd, but it works
            if is_lwjgl_3:
                depentry.suggests = suggestedVersion
                depentry.equals = suggestedVersion
            else:
                depentry.suggests = '2.9.4-nightly-20150209'
        else:
            badVersions1 = {'3.1.6', '3.2.1'}
            ourVersions = set()

            for lwjgl in iter(buckets.values()):
                ourVersions = ourVersions.union({lwjgl.version})

            if ourVersions == badVersions1:
                print("Found broken 3.1.6/3.2.1 combo, forcing LWJGL to 3.2.1")
                suggestedVersion = '3.2.1'
                depentry.suggests = suggestedVersion
            else:
                raise Exception("ERROR: cannot determine single suggested LWJGL version in %s" % mojangVersionFile.id)

        # if it uses LWJGL 3, add the trait that enables starting on first thread on macOS
        #if is_lwjgl_3:

        if not versionFile.addTraits:
            versionFile.addTraits = []
        versionFile.addTraits.append("FirstThreadOnMacOS")

        versionFile.requires = [depentry]
        versionFile.order = -2
        # process 1.13 arguments into previous version
        if not mojangVersionFile.minecraftArguments and mojangVersionFile.arguments:
            versionFile.minecraftArguments = adaptNewStyleArguments(mojangVersionFile.arguments)
        filenameOut = "multimc/net.minecraft/%s.json" % versionFile.version
        if versionFile.version in staticVersionlist.versions:
            ApplyLegacyOverride (versionFile, staticVersionlist.versions[versionFile.version])
        with open(filenameOut, 'w') as outfile:
            json.dump(versionFile.to_json(), outfile, sort_keys=True, indent=4)

def processSingleVariant(lwjglVariant):
    lwjglVersion = lwjglVariant.version
    versionObj = copy.deepcopy(lwjglVariant)
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
        # remove jutils and jinput from LWJGL 3 -- this is a dependency that Mojang kept in, but doesn't belong there anymore
        filteredLibraries = list(filter(lambda lib: not lib.name.artifact in ["jutils", "jinput"], versionObj.libraries))
        versionObj.libraries = filteredLibraries
    else:
        raise Exception("LWJGL version not recognized: %s" % versionObj.version)

    versionObj.volatile = True
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


passVariants = [
    "dc788960f7e74062aee7cee0e1e7d0a14c342418", # 2.9.0
    "cc1241e6cc967857961c7385ba078242d866d896", # 2.9.1
    "569845af361b8cd54de7153c142053425944da57", # 2.9.1-nightly-20131120
    "838930186ce1f4222f71b737ee17725d0fd14e5a", # 2.9.3
    "079b297aa801e551cc96b5e06c44e4a921807c8a", # 2.9.4-nightly-20150209
    "446142ccdcb27eca829be79702d6ff53420198a9", # 3.1.2
    "48c276ed559a4b7ca680770b110b9b60d0b2a3b9", # 3.1.6
    "4f9e33a93e5974e2ec433134983c110b3959aa31", # 3.2.1
    "15d5562e9a3d11edec17c8e2de084a96fe9f371d", # 3.2.2 - our fixed version
]

badVariants = [
    "032bfe9afc34cf1271037f734a6e7a8835fdfff0", # 2.9.0 - duplication nation
    "859f5679c60fce520a7c8cfe0c5663f848ff51ab", # 2.9.0 - broken natives
    "7811cd3ba93467842b1823ca8e571f3d49421291", # 3.1.6
    "194e5109cbdfb8d5a7da918c449b7414cd609629", # 3.2.1
    "74f2ae137e9767f0cfbe10ca9db38adaba08a4a6", # 3.2.2 - missing tinyfd
    "eaeeca768920d981bdc8ea698305f4e9723c6ba8", # 3.2.2 - missing osx natives
    "8a85feb57480e9cbb0b9c54e7b1751816122cf97", # 3.2.2 - missing other osx natives
]

# Add our own 3.2.2, with hookers and blackjack.
with open("static/lwjgl-3.2.2.json", 'r', encoding='utf-8') as lwjgl322file:
    lwjgl322 = MultiMCVersionFile(json.load(lwjgl322file))
    addLWJGLVersion(lwjglVersionVariants, lwjgl322)

for lwjglVersionVariant in lwjglVersionVariants:
    decidedVariant = None
    passedVariants = 0
    unknownVariants = 0
    print("%d variant(s) for LWJGL %s:" % (len(lwjglVersionVariants[lwjglVersionVariant]), lwjglVersionVariant))

    for variant in lwjglVersionVariants[lwjglVersionVariant]:
        if variant.sha1 in badVariants:
            print("Variant %s ignored because it's marked as bad." % (variant.sha1))
            continue
        if variant.sha1 in passVariants:
            print("Variant %s accepted." % (variant.sha1))
            decidedVariant = variant
            passedVariants += 1
            continue

        print("Variant %s:" % (variant.sha1))
        print(json.dumps(variant.version.to_json(), sort_keys=True, indent=4))
        print("")
        unknownVariants += 1
    print("")

    if decidedVariant and passedVariants == 1 and unknownVariants == 0:
        processSingleVariant(decidedVariant.version)
    else:
        raise Exception("No variant decided for version %s out of %d possible ones and %d unknown ones." % (lwjglVersionVariant, passedVariants, unknownVariants))

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
