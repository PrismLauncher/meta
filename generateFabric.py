from meta.fabricutil import *
from meta.common import ensure_component_dir, polymc_path, upstream_path, transform_maven_key
from meta.common.fabric import JARS_DIR, INSTALLER_INFO_DIR, META_DIR, INTERMEDIARY_COMPONENT, LOADER_COMPONENT

PMC_DIR = polymc_path()
UPSTREAM_DIR = upstream_path()

ensure_component_dir("net.fabricmc.fabric-loader")
ensure_component_dir("net.fabricmc.intermediary")


def load_jar_info(artifact_key):
    with open(os.path.join(UPSTREAM_DIR, JARS_DIR, f"{artifact_key}.json"), 'r',
              encoding='utf-8') as jarInfoFile:
        return FabricJarInfo(json.load(jarInfoFile))


def load_installer_info(version):
    with open(os.path.join(UPSTREAM_DIR, INSTALLER_INFO_DIR, f"{version}.json"), 'r',
              encoding='utf-8') as loaderVersionFile:
        data = json.load(loaderVersionFile)
        return FabricInstallerDataV1(data)


def process_loader_version(entry) -> PolyMCVersionFile:
    jar_info = load_jar_info(transform_maven_key(entry["maven"]))
    installer_info = load_installer_info(entry["version"])

    v = PolyMCVersionFile(name="Fabric Loader", uid="net.fabricmc.fabric-loader", version=entry["version"])
    v.releaseTime = jar_info.releaseTime
    v.requires = [DependencyEntry(uid='net.fabricmc.intermediary')]
    v.order = 10
    v.type = "release"
    if isinstance(installer_info.mainClass, dict):
        v.mainClass = installer_info.mainClass["client"]
    else:
        v.mainClass = installer_info.mainClass
    v.libraries = []
    v.libraries.extend(installer_info.libraries.common)
    v.libraries.extend(installer_info.libraries.client)
    loader_lib = PolyMCLibrary(name=GradleSpecifier(entry["maven"]), url="https://maven.fabricmc.net")
    v.libraries.append(loader_lib)
    return v


def process_intermediary_version(entry) -> PolyMCVersionFile:
    jar_info = load_jar_info(transform_maven_key(entry["maven"]))

    v = PolyMCVersionFile(name="Intermediary Mappings", uid="net.fabricmc.intermediary", version=entry["version"])
    v.releaseTime = jar_info.releaseTime
    v.requires = [DependencyEntry(uid='net.minecraft', equals=entry["version"])]
    v.order = 11
    v.type = "release"
    v.libraries = []
    v.volatile = True
    intermediary_lib = PolyMCLibrary(name=GradleSpecifier(entry["maven"]), url="https://maven.fabricmc.net")
    v.libraries.append(intermediary_lib)
    return v


def main():
    recommended_loader_versions = []
    recommended_intermediary_versions = []

    with open(os.path.join(UPSTREAM_DIR, META_DIR, "loader.json"), 'r', encoding='utf-8') as f:
        loader_version_index = json.load(f)
        for entry in loader_version_index:
            version = entry["version"]
            print(f"Processing loader {version}")

            v = process_loader_version(entry)

            if not recommended_loader_versions:  # first (newest) loader is recommended
                recommended_loader_versions.append(version)

            with open(os.path.join(PMC_DIR, LOADER_COMPONENT, f"{v.version}.json"), 'w') as outfile:
                json.dump(v.to_json(), outfile, sort_keys=True, indent=4)

    with open(os.path.join(UPSTREAM_DIR, META_DIR, "intermediary.json"), 'r', encoding='utf-8') as f:
        intermediary_version_index = json.load(f)
        for entry in intermediary_version_index:
            version = entry["version"]
            print(f"Processing intermediary {version}")

            v = process_intermediary_version(entry)

            recommended_intermediary_versions.append(version)  # all intermediaries are recommended

            with open(os.path.join(PMC_DIR, INTERMEDIARY_COMPONENT, f"{v.version}.json"), 'w') as outfile:
                json.dump(v.to_json(), outfile, sort_keys=True, indent=4)

    package = PolyMCSharedPackageData(uid=LOADER_COMPONENT, name='Fabric Loader')
    package.recommended = recommended_loader_versions
    package.description = "Fabric Loader is a tool to load Fabric-compatible mods in game environments."
    package.projectUrl = "https://fabricmc.net"
    package.authors = ["Fabric Developers"]
    package.write()

    package = PolyMCSharedPackageData(uid=INTERMEDIARY_COMPONENT, name='Intermediary Mappings')
    package.recommended = recommended_intermediary_versions
    package.description = "Intermediary mappings allow using Fabric Loader with mods for Minecraft in a more compatible manner."
    package.projectUrl = "https://fabricmc.net"
    package.authors = ["Fabric Developers"]
    package.write()


if __name__ == '__main__':
    main()
