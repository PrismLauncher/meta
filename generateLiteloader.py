#!/usr/bin/python
from liteloaderutil import *
from jsonobject import *
from datetime import datetime
from pprint import pprint
import copy

# load the locally cached version list
def loadLiteloaderJson():
    with open("upstream/liteloader/versions.json", 'r', encoding='utf-8') as f:
        return LiteloaderIndex(json.load(f))

remoteVersionlist = loadLiteloaderJson()

def processArtefacts(mcVersion, liteloader, notSnapshots):
    versions = []
    lookup = {}
    latestVersion = None
    latest = None
    for id, artefact in liteloader.items():
        if id == 'latest':
            latestVersion = artefact.version
            continue
        version = MultiMCVersionFile(name="LiteLoader", uid="com.mumfrey.liteloader", version=artefact.version)
        version.requires = {}
        version.requires['net.minecraft'] = mcVersion
        version.releaseTime = datetime.utcfromtimestamp(int(artefact.timestamp))
        version.addTweakers = [artefact.tweakClass]
        version.order = 10
        if notSnapshots:
            version.type = "release"
        else:
            version.type = "snapshot"
        lookup[version.version] = version
        libraries = artefact.libraries
        # hack to make liteloader 1.7.10_00 work
        for lib in libraries:
            if lib.name == GradleSpecifier("org.ow2.asm:asm-all:5.0.3"):
                lib.url = "http://repo.maven.apache.org/maven2/"
        liteloaderLib = MultiMCLibrary(
            name=GradleSpecifier("com.mumfrey:liteloader:%s" % version.version),
            url = "http://dl.liteloader.com/versions/"
        )
        if not notSnapshots:
            liteloaderLib.mmcHint = "always-stale"
        libraries.append(liteloaderLib)
        version.libraries = libraries
        versions.append(version)
    if latestVersion:
        latest = lookup[latestVersion]
    return versions, latest

allVersions = []
latest = []
recommended = []
for mcVersion, versionObject in remoteVersionlist.versions.items():
    # ignore this for now. It should be a jar mod or something.
    if mcVersion == "1.5.2":
        continue
    latestSnapshot = None
    latestRelease = None
    version = []
    if versionObject.artefacts:
        versions, latestRelease = processArtefacts(mcVersion, versionObject.artefacts.liteloader, True)
        allVersions.extend(versions)
    if versionObject.snapshots:
        versions, latestSnapshot = processArtefacts(mcVersion, versionObject.snapshots.liteloader, False)
        allVersions.extend(versions)

    if latestSnapshot:
        latest.append(latestSnapshot)
    elif latestRelease:
        latest.append(latestRelease)
    if latestRelease:
        recommended.append(latestRelease)

allVersions.sort(key=lambda x: x.releaseTime, reverse=True)

for version in allVersions:
    outFilepath = "multimc/com.mumfrey.liteloader/%s.json" % version.version
    with open(outFilepath, 'w') as outfile:
        json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

writeSharedPackageData('com.mumfrey.liteloader', 'LiteLoader', 'net.minecraft')
