import copy
import datetime
import hashlib
import json
import os
from collections import defaultdict, namedtuple
from distutils import version
from operator import itemgetter
from pprint import pprint

import iso8601
from metautil import *

PMC_DIR = os.environ["PMC_DIR"]
UPSTREAM_DIR = os.environ["UPSTREAM_DIR"]

LOG4J_VERSION_OVERRIDE = "2.17.1"  # This is the only version that's patched (as of 2022/02/18)
LOG4J_MAVEN_REPO = "https://repo1.maven.org/maven2/%s"

LOG4J_HASHES = {
    "log4j-api": {
        "sha1": "d771af8e336e372fb5399c99edabe0919aeaf5b2",
        "size": 301872
    },
    "log4j-core": {
        "sha1": "779f60f3844dadc3ef597976fcb1e5127b1f343d",
        "size": 1790452
    },
    "log4j-slf4j18-impl": {
        "sha1": "ca499d751f4ddd8afb016ef698c30be0da1d09f7",
        "size": 21268
    }
};

# LWJGL versions we want
passVariants = [
    "41d3ed7a755d15ad9e2f5a8aea51481858d60763", # 3.2.2 (2021-12-10 03:36:38+00:00)
    "57455f0bb479e07e5b554766f9f0310a6c245e10", # 3.1.2 (2018-06-21 12:57:11+00:00)
    "abfbb7905498983ab3300ae2b897ccd3c11ab8bb", # 2.9.0 (2013-10-21 16:34:47+00:00)
    "47fd9d3677d7a0bcdb280453a7e7ac1fdbdab70d", # 2.9.4-nightly-20150209 (2016-12-20 14:05:34+00:00)
    "8ee2407d76c3af7882ab897b6ef25392839d2ab0", # 3.1.6 (2019-04-18 11:05:19+00:00)
    "428282d96ee546aae07d0717fef71ab8213d1176", # 3.2.1 (2019-04-18 11:05:19+00:00)
    "c7a84795ac3197bb476949665f3eda9c79436cf7", # 2.9.1 (2014-05-22 14:44:33+00:00)
    "66a60d78abe20960f1befd0fd5819a8855100055", # 2.9.1-nightly-20131120 (2013-12-06 13:55:34+00:00)
    "15a92ddad26186e720117fc0e318c6ddb8bae14e", # 2.9.3 (2015-01-30 11:58:24+00:00)
]

# LWJGL versions we def. don't want!
badVariants = [
    "089446ef48f6ac70a3e2bc4a02cd1f34060d31bd", # 3.2.2 (2021-08-25 14:41:57+00:00)
    "6a0aaa55846ebccae9cf69e1ac2e284b3f0d81d0", # 3.2.2 (2019-07-19 09:25:47+00:00)
    "e3ecb31817e009ebfb3a8ed41b7b779d31e55b43", # 3.2.2 (2019-07-04 14:41:05+00:00)
    "2d0b7aa8397278c5b5f7e9cd025544af5e820072", # 2.9.0 (2013-09-06 12:31:58+00:00)
    "905c3a9d80a804c2d03a577775b75f45c1837263", # 2.9.0 (2011-03-30 22:00:00+00:00)
    "d889b127fbabd3493115beb228730146072549a4", # 3.1.6 (2018-11-29 13:11:38+00:00)
    "0034e86cec334f9142ca4ace843c91eb649017fd", # 3.2.1 (2019-02-13 16:12:08+00:00)
]

def addOrGetBucket(buckets, rules):
    ruleHash = None
    if rules:
        ruleHash = hash(json.dumps(rules.to_json()))

    bucket = None
    if ruleHash in buckets:
        bucket = buckets[ruleHash]
    else:
        bucket = PolyMCVersionFile(
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
    lwjglObjectCopy.releaseTime = datetime.datetime.fromtimestamp(0)
    return hashlib.sha1(json.dumps(lwjglObjectCopy.to_json(), sort_keys=True).encode("utf-8", "strict")).hexdigest()

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
    if pmcLib.downloads.artifact:
        pmcLib.downloads.artifact.path = None
    if pmcLib.downloads.classifiers:
        for key, value in pmcLib.downloads.classifiers.items():
            value.path = None

def adaptNewStyleArguments(arguments):
    outarr = []
    # we ignore the jvm arguments entirely.
    # grab the strings, log the complex stuff
    for arg in arguments.game:
        if isinstance(arg, str):
            if arg == '--clientId':
                continue
            if arg == '${clientid}':
                continue
            if arg == '--xuid':
                continue
            if arg == '${auth_xuid}':
                continue
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

for filename in os.listdir(UPSTREAM_DIR + '/mojang/versions'):
    with open(UPSTREAM_DIR + "/mojang/versions/" + filename) as json_file:
        print("Processing", filename)
        mojangVersionFile = MojangVersionFile(json.load(json_file))
        versionFile = MojangToPolyMC(mojangVersionFile, "Minecraft", "net.minecraft", mojangVersionFile.id)
        libs_minecraft = []
        is_lwjgl_3 = False
        buckets = {}
        for lib in versionFile.libraries:
            pmcLib = PolyMCLibrary(lib.to_json())
            removePathsFromLib(pmcLib)
            specifier = pmcLib.name
            ruleHash = None
            if specifier.isLwjgl():
                rules = None
                if pmcLib.rules:
                    rules = pmcLib.rules
                    pmcLib.rules = None
                if isOnlyMacOS(rules, specifier):
                    print("Candidate library ",  specifier, " is only for macOS and is therefore ignored.")
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
                bucket.libraries.append(pmcLib)
                bucket.releaseTime = versionFile.releaseTime
            else:
                # FIXME: workaround for insane log4j nonsense from December 2021. Probably needs adjustment.
                if pmcLib.name.isLog4j():
                    replacementLib = PolyMCLibrary(name=GradleSpecifier("org.apache.logging.log4j:%s:%s" % (pmcLib.name.artifact, LOG4J_VERSION_OVERRIDE)))
                    replacementLib.downloads = MojangLibraryDownloads()
                    replacementLib.downloads.artifact = MojangArtifact()
                    replacementLib.downloads.artifact.url = LOG4J_MAVEN_REPO % (replacementLib.name.getPath())
                    replacementLib.downloads.artifact.sha1 = LOG4J_HASHES[pmcLib.name.artifact]["sha1"]
                    replacementLib.downloads.artifact.size = LOG4J_HASHES[pmcLib.name.artifact]["size"]
                    if pmcLib.name.artifact not in LOG4J_HASHES:
                        raise Exception("ERROR: unhandled log4j artifact %s!" % pmcLib.name.artifact)
                    libs_minecraft.append(replacementLib)
                else:
                    libs_minecraft.append(pmcLib)
        if len(buckets) == 1:
            for key in buckets:
                keyBucket = buckets[key]
                keyBucket.libraries = sorted(keyBucket.libraries, key=itemgetter('name'))
                addLWJGLVersion(lwjglVersionVariants, keyBucket)
                print("Found only candidate LWJGL", keyBucket.version, key)
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
        if is_lwjgl_3:
            if not versionFile.addTraits:
                versionFile.addTraits = []
            versionFile.addTraits.append("FirstThreadOnMacOS")
        versionFile.requires = [depentry]
        versionFile.order = -2
        # process 1.13 arguments into previous version
        if not mojangVersionFile.minecraftArguments and mojangVersionFile.arguments:
            versionFile.minecraftArguments = adaptNewStyleArguments(mojangVersionFile.arguments)
        filenameOut = PMC_DIR + "/net.minecraft/%s.json" % versionFile.version
        if versionFile.version in staticVersionlist.versions:
            ApplyLegacyOverride (versionFile, staticVersionlist.versions[versionFile.version])
        with open(filenameOut, 'w') as outfile:
            json.dump(versionFile.to_json(), outfile, sort_keys=True, indent=4)

def processSingleVariant(lwjglVariant):
    lwjglVersion = lwjglVariant.version
    versionObj = copy.deepcopy(lwjglVariant)
    if lwjglVersion[0] == '2':
        filename = PMC_DIR + "/org.lwjgl/%s.json" % lwjglVersion
        versionObj.name = 'LWJGL 2'
        versionObj.uid = 'org.lwjgl'
        versionObj.conflicts = [DependencyEntry(uid='org.lwjgl3')]
    elif lwjglVersion[0] == '3':
        filename = PMC_DIR + "/org.lwjgl3/%s.json" % lwjglVersion
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

        print(f"    \"{variant.sha1}\", # {lwjglVersionVariant} ({variant.version.releaseTime})")
        unknownVariants += 1
    print("")

    if decidedVariant and passedVariants == 1 and unknownVariants == 0:
        processSingleVariant(decidedVariant.version)
    else:
        raise Exception("No variant decided for version %s out of %d possible ones and %d unknown ones." % (lwjglVersionVariant, passedVariants, unknownVariants))

lwjglSharedData = PolyMCSharedPackageData(uid = 'org.lwjgl', name = 'LWJGL 2')
lwjglSharedData.recommended = ['2.9.4-nightly-20150209']
lwjglSharedData.write()

if found_any_lwjgl3:
    lwjglSharedData = PolyMCSharedPackageData(uid = 'org.lwjgl3', name = 'LWJGL 3')
    lwjglSharedData.recommended = ['3.1.2']
    lwjglSharedData.write()

with open(UPSTREAM_DIR + "/mojang/version_manifest_v2.json", 'r', encoding='utf-8') as localIndexFile:
    localVersionlist = MojangIndexWrap(json.load(localIndexFile))

mcSharedData = PolyMCSharedPackageData(uid = 'net.minecraft', name = 'Minecraft')
mcSharedData.recommended = [localVersionlist.latest['release']]
mcSharedData.write()
