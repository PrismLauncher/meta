from fabricutil import *

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


mkdirs(PMC_DIR + "/org.quiltmc.quilt-loader")
mkdirs(PMC_DIR + "/org.quiltmc.quilt-mappings")


def loadJarInfo(mavenKey):
    with open(UPSTREAM_DIR + "/quilt/jars/" + mavenKey.replace(":", ".") + ".json", 'r',
              encoding='utf-8') as jarInfoFile:
        return FabricJarInfo(json.load(jarInfoFile))


def processLoaderVersion(loaderVersion, it, loaderData):
    if (len(loaderRecommended) < 1):  # TODO figure out actual stable version
        loaderRecommended.append(loaderVersion)
    versionJarInfo = loadJarInfo(it["maven"])
    version = PolyMCVersionFile(name="Quilt Loader", uid="org.quiltmc.quilt-loader", version=loaderVersion)
    version.releaseTime = versionJarInfo.releaseTime
    version.requires = [DependencyEntry(uid='org.quiltmc.quilt-mappings')]
    version.order = 10
    version.type = "release"
    if isinstance(loaderData.mainClass, dict):
        version.mainClass = loaderData.mainClass["client"]
    else:
        version.mainClass = loaderData.mainClass
    version.libraries = []
    version.libraries.extend(loaderData.libraries.common)
    version.libraries.extend(loaderData.libraries.client)
    loaderLib = PolyMCLibrary(name=GradleSpecifier(it["maven"]), url="https://maven.quiltmc.org/repository/release")
    version.libraries.append(loaderLib)
    loaderVersions.append(version)


def processIntermediaryVersion(it):
    intermediaryRecommended.append(it["version"])
    versionJarInfo = loadJarInfo(it["maven"])
    version = PolyMCVersionFile(name="Quilt Intermediary Mappings", uid="org.quiltmc.quilt-mappings", version=it["version"])
    version.releaseTime = versionJarInfo.releaseTime
    version.requires = [DependencyEntry(uid='net.minecraft', equals=it["version"])]
    version.order = 11
    version.type = "release"
    version.libraries = []
    version.volatile = True
    mappingLib = PolyMCLibrary(name=GradleSpecifier(it["maven"]), url="https://maven.quiltmc.org/repository/release")
    version.libraries.append(mappingLib)
    intermediaryVersions.append(version)


with open(UPSTREAM_DIR + "/quilt/meta-v3/loader.json", 'r', encoding='utf-8') as loaderVersionIndexFile:
    loaderVersionIndex = json.load(loaderVersionIndexFile)
    for it in loaderVersionIndex:
        version = it["version"]
        with open(UPSTREAM_DIR + "/quilt/loader-installer-json/" + version + ".json", 'r',
                  encoding='utf-8') as loaderVersionFile:
            ldata = json.load(loaderVersionFile)
            ldata = FabricInstallerDataV1(ldata)
            processLoaderVersion(version, it, ldata)

with open(UPSTREAM_DIR + "/quilt/meta-v3/quilt-mappings.json", 'r', encoding='utf-8') as intermediaryVersionIndexFile:
    intermediaryVersionIndex = json.load(intermediaryVersionIndexFile)
    for it in intermediaryVersionIndex:
        processIntermediaryVersion(it)

for version in loaderVersions:
    outFilepath = PMC_DIR + "/org.quiltmc.quilt-loader/%s.json" % version.version
    with open(outFilepath, 'w') as outfile:
        json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

sharedData = PolyMCSharedPackageData(uid='org.quiltmc.quilt-loader', name='Quilt Loader')
sharedData.recommended = loaderRecommended
sharedData.description = "The Quilt project is an open, community-driven modding toolchain designed primarily for Minecraft."
sharedData.projectUrl = "https://quiltmc.org"
sharedData.authors = ["Quilt Project"]
sharedData.write()

for version in intermediaryVersions:
    outFilepath = PMC_DIR + "/org.quiltmc.quilt-mappings/%s.json" % version.version
    with open(outFilepath, 'w') as outfile:
        json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

sharedData = PolyMCSharedPackageData(uid='org.quiltmc.quilt-mappings', name='Quilt Intermediary Mappings')
sharedData.recommended = intermediaryRecommended
sharedData.description = "Intermediary mappings allow using Quilt Loader with mods for Minecraft in a more compatible manner."
sharedData.projectUrl = "https://quiltmc.org"
sharedData.authors = ["Quilt Project"]
sharedData.write()
