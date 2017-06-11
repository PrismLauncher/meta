#!/usr/bin/python
from __future__ import print_function
import sys
import os
import re
from metautil import *
from forgeutil import *
from jsonobject import *
from distutils.version import LooseVersion

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Contruct a set of libraries out of a Minecraft version file, for filtering.
mcVersionCache = {}
def loadMcVersionFilter(version):
    if version in mcVersionCache:
        return mcVersionCache[version]
    libSet = set()
    with open("multimc/net.minecraft/%s.json" % version, 'r', encoding='utf-8') as mcFile:
        mcVersion = MultiMCVersionFile(json.load(mcFile))
        for lib in mcVersion.libraries:
            libSet.add(lib.name)
        mcVersionCache[version] = libSet
        return libSet

'''
Match a library coordinate to a set of library coordinates.
 * Block those that pass completely.
 * For others, block those with lower versions than in the set.
'''
def shouldIgnoreArtifact(libSet, match):
    for ver in libSet:
        if ver.group == match.group and ver.artifact == match.artifact and ver.classifier == match.classifier:
            if ver.version == match.version:
                # Everything is matched perfectly - this one will be ignored
                return True
            else:
                # We say the lib matches (is the same) also when the new version is lower than the old one
                if LooseVersion(ver.version) > LooseVersion(match.version):
                    # eprint ("Lower version on %s:%s:%s: OLD=%s NEW=%s" % (ver.group, ver.artifact, ver.classifier, ver.version, match.version))
                    return True
                # Otherwise it did not match - new version is higher and this is an upgrade
                return False
    # No match found in the set - we need to keep this
    return False

def versionFromProfile(profile, version):
    result = MultiMCVersionFile({"name":"Forge", "version":version.rawVersion, "uid":"net.minecraftforge" })
    mcversion = profile.install.minecraft
    result.parentUid ='net.minecraft'
    result.requires ={'net.minecraft': mcversion}
    result.mainClass = profile.versionInfo.mainClass
    args = profile.versionInfo.minecraftArguments
    tweakers = []
    expression = re.compile("--tweakClass ([a-zA-Z0-9\\.]+)")
    match = expression.search(args)
    while match != None:
        tweakers.append(match.group(1));
        args = args[:match.start()] + args[match.end():]
        match = expression.search(args);
    if len(tweakers) > 0:
        args = args.strip()
        result.addTweakers = tweakers;
    # result.minecraftArguments = args
    result.releaseTime = profile.versionInfo.time
    libs = []
    mcFilter = loadMcVersionFilter(mcversion)
    for forgeLib in profile.versionInfo.libraries:
        if forgeLib.name.isLwjgl():
            continue
        if shouldIgnoreArtifact(mcFilter, forgeLib.name):
            continue
        fixedName = forgeLib.name
        if fixedName.group == "net.minecraftforge":
            if fixedName.artifact == "minecraftforge":
                fixedName.artifact = "forge"
                fixedName.classifier = "universal"
                fixedName.version = "%s-%s" % (mcversion, fixedName.version)
            elif fixedName.artifact == "forge":
                fixedName.classifier = "universal"
        ourLib = MultiMCLibrary(name=fixedName)
        ourLib.url = forgeLib.url
        if forgeLib.checksums and len(forgeLib.checksums) == 2:
            ourLib.mmcHint = "forge-pack-xz"
        libs.append(ourLib)
    result.libraries = libs
    result.order = 5
    return result

def versionFromLegacy(version, legacyinfo : ForgeLegacyInfo):
    result = MultiMCVersionFile({"name":"Forge", "version":version.rawVersion, "uid":"net.minecraftforge" })
    mcversion = version.mcversion_sane
    result.parentUid ='net.minecraft'
    result.requires ={'net.minecraft': mcversion}
    result.releaseTime = legacyinfo.releaseTime
    result.order = 5
    if mcversion in fmlLibsMapping:
        result.addTraits = ["legacyFML"]
    url = version.url()
    classifier = None
    if "universal" in url:
        classifier = "universal"
    else:
        classifier = "client"
    coord = GradleSpecifier("net.minecraftforge:forge:%s:%s" % (version.longVersion,classifier))
    mainmod = MultiMCLibrary(name = coord)
    mainmod.downloads = MojangLibraryDownloads()
    mainmod.downloads.artifact = MojangArtifact()
    mainmod.downloads.artifact.path = None
    mainmod.downloads.artifact.url = version.url()
    mainmod.downloads.artifact.sha1 = legacyinfo.sha1
    mainmod.downloads.artifact.size = legacyinfo.size
    result.jarMods = [mainmod]
    return result

# load the locally cached version list
with open("upstream/forge/index.json", 'r', encoding='utf-8') as f:
    main_json = json.load(f)
    remoteVersionlist = ForgeIndex(main_json)

recommendedIds = set([v for k, v in remoteVersionlist.promos.items() if 'recommended' in k])
recommendedVersions = []
print ('Recommended IDs:', recommendedIds)

tsPath = "static/forge-legacyinfo.json"

legacyinfolist = None
with open(tsPath, 'r', encoding='utf-8') as tsFile:
    legacyinfolist = ForgeLegacyInfoList(json.load(tsFile))

for id, entry in remoteVersionlist.number.items():
    if entry.mcversion == None:
        eprint ("Skipping %d with invalid MC version" % entry.build)
        continue

    version = ForgeVersion(entry, remoteVersionlist.artifact, remoteVersionlist.webpath)
    if version.url() == None:
        eprint ("Skipping %d with no valid files" % version.build)
        continue

    if int(id) in recommendedIds:
        recommendedVersions.append(version.rawVersion)

    # If we do not have the corresponding Minecraft version, we ignore it
    if not os.path.isfile("multimc/net.minecraft/%s.json" % version.mcversion_sane):
        eprint ("Skipping %d with no corresponding Minecraft version %s" % (version.build, version.mcversion_sane))
        continue

    outVersion = None

    if version.usesInstaller():
        profileFilepath = "upstream/forge/%s.json" % version.longVersion
        # If we do not have the Forge json, we ignore this version
        if not os.path.isfile(profileFilepath):
            eprint ("Skipping %d with missing profile json" % version.build)
            continue
        with open(profileFilepath, 'r', encoding='utf-8') as profileFile:
            profile = ForgeInstallerProfile(json.load(profileFile))
            outVersion = versionFromProfile(profile, version)
    else:
        # Generate json for legacy here
        if version.mcversion_sane == "1.6.1":
            continue
        if not id in legacyinfolist.number:
            print("Legacy id", id, "is missing in legacy info. Ignoring.")
            continue

        outVersion = versionFromLegacy(version, legacyinfolist.number[id])

    outFilepath = "multimc/net.minecraftforge/%s.json" % outVersion.version
    with open(outFilepath, 'w') as outfile:
        json.dump(outVersion.to_json(), outfile, sort_keys=True, indent=4)

print ('Recommended versions:', recommendedVersions)

sharedData = MultiMCSharedPackageData(uid = 'net.minecraftforge', name = "Forge", parentUid = 'net.minecraft')
sharedData.projectUrl = 'http://www.minecraftforge.net/forum/'
sharedData.recommended = recommendedVersions
sharedData.write()
