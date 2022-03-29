import json
import os

from meta.common import ensure_component_dir, polymc_path, upstream_path, transform_maven_key
from meta.common.fabric import JARS_DIR, INSTALLER_INFO_DIR, META_DIR, INTERMEDIARY_COMPONENT, LOADER_COMPONENT
from meta.model import MetaVersionFile, Dependency, Library, MetaPackageData
from meta.model.fabric import FabricJarInfo, FabricInstallerDataV1, FabricMainClasses
from meta.model.types import GradleSpecifier

PMC_DIR = polymc_path()
UPSTREAM_DIR = upstream_path()

ensure_component_dir("net.fabricmc.fabric-loader")
ensure_component_dir("net.fabricmc.intermediary")


def load_jar_info(artifact_key) -> FabricJarInfo:
    return FabricJarInfo.parse_file(os.path.join(UPSTREAM_DIR, JARS_DIR, f"{artifact_key}.json"))


def load_installer_info(version) -> FabricInstallerDataV1:
    return FabricInstallerDataV1.parse_file(os.path.join(UPSTREAM_DIR, INSTALLER_INFO_DIR, f"{version}.json"))


def process_loader_version(entry) -> MetaVersionFile:
    jar_info = load_jar_info(transform_maven_key(entry["maven"]))
    installer_info = load_installer_info(entry["version"])

    v = MetaVersionFile(name="Fabric Loader", uid="net.fabricmc.fabric-loader", version=entry["version"])
    v.release_time = jar_info.release_time
    v.requires = [Dependency(uid='net.fabricmc.intermediary')]
    v.order = 10
    v.type = "release"
    if isinstance(installer_info.main_class, FabricMainClasses):
        v.main_class = installer_info.main_class.client
    else:
        v.main_class = installer_info.main_class
    v.libraries = []
    v.libraries.extend(installer_info.libraries.common)
    v.libraries.extend(installer_info.libraries.client)
    loader_lib = Library(name=GradleSpecifier(entry["maven"]), url="https://maven.fabricmc.net")
    v.libraries.append(loader_lib)
    return v


def process_intermediary_version(entry) -> MetaVersionFile:
    jar_info = load_jar_info(transform_maven_key(entry["maven"]))

    v = MetaVersionFile(name="Intermediary Mappings", uid="net.fabricmc.intermediary", version=entry["version"])
    v.release_time = jar_info.release_time
    v.requires = [Dependency(uid='net.minecraft', equals=entry["version"])]
    v.order = 11
    v.type = "release"
    v.libraries = []
    v.volatile = True
    intermediary_lib = Library(name=GradleSpecifier(entry["maven"]), url="https://maven.fabricmc.net")
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

            v.write(os.path.join(PMC_DIR, LOADER_COMPONENT, f"{v.version}.json"))

    with open(os.path.join(UPSTREAM_DIR, META_DIR, "intermediary.json"), 'r', encoding='utf-8') as f:
        intermediary_version_index = json.load(f)
        for entry in intermediary_version_index:
            version = entry["version"]
            print(f"Processing intermediary {version}")

            v = process_intermediary_version(entry)

            recommended_intermediary_versions.append(version)  # all intermediaries are recommended

            v.write(os.path.join(PMC_DIR, INTERMEDIARY_COMPONENT, f"{v.version}.json"))

    package = MetaPackageData(uid=LOADER_COMPONENT, name='Fabric Loader')
    package.recommended = recommended_loader_versions
    package.description = "Fabric Loader is a tool to load Fabric-compatible mods in game environments."
    package.project_url = "https://fabricmc.net"
    package.authors = ["Fabric Developers"]
    package.write(os.path.join(PMC_DIR, LOADER_COMPONENT, "package.json"))

    package = MetaPackageData(uid=INTERMEDIARY_COMPONENT, name='Intermediary Mappings')
    package.recommended = recommended_intermediary_versions
    package.description = "Intermediary mappings allow using Fabric Loader with mods for Minecraft in a more compatible manner."
    package.project_url = "https://fabricmc.net"
    package.authors = ["Fabric Developers"]
    package.write(os.path.join(PMC_DIR, INTERMEDIARY_COMPONENT, "package.json"))


if __name__ == '__main__':
    main()
