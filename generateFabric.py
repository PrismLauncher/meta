import copy
import os
from datetime import datetime
from pprint import pprint

from fabricutil import *
from jsonobject import *

PMC_DIR = os.environ["PMC_DIR"]
UPSTREAM_DIR = os.environ["UPSTREAM_DIR"]

# turn loader versions into packages
loaderRecommended = []
loaderVersions = []
intermediaryRecommended = []
intermediaryVersions = []

def mkdirs(path):
    if not os.path.exists(path):
        os.makedirs(path)

mkdirs(PMC_DIR + "/net.fabricmc.fabric-loader")
mkdirs(PMC_DIR + "/net.fabricmc.intermediary")

def loadJarInfo(mavenKey):
    with open(UPSTREAM_DIR + "/fabric/jars/" + mavenKey.replace(":", ".") + ".json", 'r', encoding='utf-8') as jarInfoFile:
        return FabricJarInfo(json.load(jarInfoFile))

def processLoaderVersion(loaderVersion, it, loaderData):
    verStable = it["stable"]
    if (len(loaderRecommended) < 1) and verStable:
        loaderRecommended.append(loaderVersion)
    versionJarInfo = loadJarInfo(it["maven"])
    version = PolyMCVersionFile(name="Fabric Loader", uid="net.fabricmc.fabric-loader", version=loaderVersion)
    version.releaseTime = versionJarInfo.releaseTime
    version.requires = [DependencyEntry(uid='net.fabricmc.intermediary')]
    version.order = 10
    version.type = "release"
    if isinstance(loaderData.mainClass, dict):
        version.mainClass = loaderData.mainClass["client"]
    else:
        version.mainClass = loaderData.mainClass
    version.libraries = []
    version.libraries.extend(loaderData.libraries.common)
    version.libraries.extend(loaderData.libraries.client)
    loaderLib = PolyMCLibrary(name=GradleSpecifier(it["maven"]), url="https://maven.fabricmc.net")
    version.libraries.append(loaderLib)
    loaderVersions.append(version)

def processIntermediaryVersion(it):
    intermediaryRecommended.append(it["version"])
    versionJarInfo = loadJarInfo(it["maven"])
    version = PolyMCVersionFile(name="Intermediary Mappings", uid="net.fabricmc.intermediary", version=it["version"])
    version.releaseTime = versionJarInfo.releaseTime
    version.requires = [DependencyEntry(uid='net.minecraft', equals=it["version"])]
    version.order = 11
    version.type = "release"
    version.libraries = []
    version.volatile = True
    mappingLib = PolyMCLibrary(name=GradleSpecifier(it["maven"]), url="https://maven.fabricmc.net")
    version.libraries.append(mappingLib)
    intermediaryVersions.append(version)

with open(UPSTREAM_DIR + "/fabric/meta-v2/loader.json", 'r', encoding='utf-8') as loaderVersionIndexFile:
    loaderVersionIndex = json.load(loaderVersionIndexFile)
    for it in loaderVersionIndex:
        version = it["version"]
        with open(UPSTREAM_DIR + "/fabric/loader-installer-json/" + version + ".json", 'r', encoding='utf-8') as loaderVersionFile:
            ldata = json.load(loaderVersionFile)
            ldata = FabricInstallerDataV1(ldata)
            processLoaderVersion(version, it, ldata)

with open(UPSTREAM_DIR + "/fabric/meta-v2/intermediary.json", 'r', encoding='utf-8') as intermediaryVersionIndexFile:
    intermediaryVersionIndex = json.load(intermediaryVersionIndexFile)
    for it in intermediaryVersionIndex:
        processIntermediaryVersion(it)

for version in loaderVersions:
    outFilepath = PMC_DIR + "/net.fabricmc.fabric-loader/%s.json" % version.version
    with open(outFilepath, 'w') as outfile:
        json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

sharedData = PolyMCSharedPackageData(uid = 'net.fabricmc.fabric-loader', name = 'Fabric Loader')
sharedData.recommended = loaderRecommended
sharedData.description = "Fabric Loader is a tool to load Fabric-compatible mods in game environments."
sharedData.projectUrl = "https://fabricmc.net"
sharedData.authors = ["Fabric Developers"]
sharedData.write()

for version in intermediaryVersions:
    outFilepath = PMC_DIR + "/net.fabricmc.intermediary/%s.json" % version.version
    with open(outFilepath, 'w') as outfile:
        json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

sharedData = PolyMCSharedPackageData(uid = 'net.fabricmc.intermediary', name = 'Intermediary Mappings')
sharedData.recommended = intermediaryRecommended
sharedData.description = "Intermediary mappings allow using Fabric Loader with mods for Minecraft in a more compatible manner."
sharedData.projectUrl = "https://fabricmc.net"
sharedData.authors = ["Fabric Developers"]
sharedData.write()
