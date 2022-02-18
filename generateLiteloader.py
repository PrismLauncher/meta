import copy
import os
import datetime
from pprint import pprint

from jsonobject import *
from liteloaderutil import *

PMC_DIR = os.environ["PMC_DIR"]
UPSTREAM_DIR = os.environ["UPSTREAM_DIR"]

# load the locally cached version list
def loadLiteloaderJson():
    with open(UPSTREAM_DIR + "/liteloader/versions.json", 'r', encoding='utf-8') as f:
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
        version = PolyMCVersionFile(name="LiteLoader", uid="com.mumfrey.liteloader", version=artefact.version)
        version.requires = [DependencyEntry(uid='net.minecraft', equals=mcVersion)]
        version.releaseTime = datetime.datetime.utcfromtimestamp(int(artefact.timestamp))
        version.addTweakers = [artefact.tweakClass]
        version.mainClass = "net.minecraft.launchwrapper.Launch"
        version.order = 10
        if notSnapshots:
            version.type = "release"
        else:
            version.type = "snapshot"
        lookup[version.version] = version
        libraries = artefact.libraries
        # hack to make broken liteloader versions work
        for lib in libraries:
            if lib.name == GradleSpecifier("org.ow2.asm:asm-all:5.0.3"):
                lib.url = "https://repo.maven.apache.org/maven2/"
            if lib.name == GradleSpecifier("org.ow2.asm:asm-all:5.2"):
                lib.url = "http://repo.liteloader.com/"
        liteloaderLib = PolyMCLibrary(
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

    if latestRelease:
        recommended.append(latestRelease.version)

recommended.sort()

allVersions.sort(key=lambda x: x.releaseTime, reverse=True)

for version in allVersions:
    outFilepath = PMC_DIR + "/com.mumfrey.liteloader/%s.json" % version.version
    with open(outFilepath, 'w') as outfile:
        json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

sharedData = PolyMCSharedPackageData(uid = 'com.mumfrey.liteloader', name = 'LiteLoader')
sharedData.recommended = recommended
sharedData.description = remoteVersionlist.meta.description
sharedData.projectUrl = remoteVersionlist.meta.url
sharedData.authors = [remoteVersionlist.meta.authors]
sharedData.write()
