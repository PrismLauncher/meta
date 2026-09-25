import json
import os

from meta.common import (
    ensure_component_dir,
    launcher_path,
    upstream_path,
    transform_maven_key,
    eprint,
)
from meta.common.mojang import MINECRAFT_COMPONENT
from meta.common.ornithe import (
    JARS_DIR,
    LIBRARIES_DIR,
    LWJGL_DIR,
    META_DIR,
    MAVEN_URL,
    INTERMEDIARY_COMPONENT,
    JAVA_MAJORS,
    JAVA_NAME,
    LOADERS,
)
from meta.model import MetaVersion, Dependency, Library, MetaPackage, GradleSpecifier
from meta.model.fabric import FabricJarInfo, FabricInstallerDataV1, FabricMainClasses

LAUNCHER_DIR = launcher_path()
UPSTREAM_DIR = upstream_path()


def load_jar_info(jars_dir, maven_key) -> FabricJarInfo:
    return FabricJarInfo.parse_file(
        os.path.join(UPSTREAM_DIR, jars_dir, f"{transform_maven_key(maven_key)}.json")
    )


def load_upstream_json(*path):
    with open(os.path.join(UPSTREAM_DIR, *path), encoding="utf-8") as f:
        return json.load(f)


def has_minecraft_version(version):
    return os.path.isfile(
        os.path.join(LAUNCHER_DIR, MINECRAFT_COMPONENT, f"{version}.json")
    )


def process_intermediary_version(entry) -> MetaVersion:
    version = entry["version"]
    jar_info = load_jar_info(JARS_DIR, entry["maven"])
    library_upgrades = load_upstream_json(LIBRARIES_DIR, f"{version}.json")
    lwjgl_upgrades = load_upstream_json(LWJGL_DIR, f"{version}.json")

    v = MetaVersion(
        name="Calamus Intermediary Mappings",
        uid=INTERMEDIARY_COMPONENT,
        version=version,
    )
    v.release_time = jar_info.release_time
    v.requires = [Dependency(uid=MINECRAFT_COMPONENT, equals=version)]
    v.type = "release"
    v.volatile = True
    v.libraries = [
        Library(name=GradleSpecifier.from_string(entry["maven"]), url=MAVEN_URL)
    ]
    v.libraries.extend(
        Library(name=GradleSpecifier.from_string(lib["name"]), url=lib["url"])
        for lib in library_upgrades
    )
    v.libraries.extend(Library.parse_obj(lib) for lib in lwjgl_upgrades)
    v.additional_jvm_args = [
        f"-D{loader['prefix']}.gameVersion={version}" for loader in LOADERS.values()
    ]
    v.compatible_java_majors = JAVA_MAJORS
    v.compatible_java_name = JAVA_NAME
    return v


def process_loader_version(loader, entry) -> MetaVersion:
    version = entry["version"]
    jar_info = load_jar_info(loader["jars_dir"], entry["maven"])
    installer_info = FabricInstallerDataV1.parse_file(
        os.path.join(UPSTREAM_DIR, loader["installer_info_dir"], f"{version}.json")
    )

    v = MetaVersion(name=loader["name"], uid=loader["uid"], version=version)
    v.release_time = jar_info.release_time
    v.requires = [Dependency(uid=INTERMEDIARY_COMPONENT)]
    v.type = "release"
    if isinstance(installer_info.main_class, FabricMainClasses):
        v.main_class = installer_info.main_class.client
    else:
        v.main_class = installer_info.main_class
    v.libraries = []
    v.libraries.extend(installer_info.libraries.common)
    v.libraries.extend(installer_info.libraries.client)
    v.libraries.append(
        Library(name=GradleSpecifier.from_string(entry["maven"]), url=loader["maven"])
    )
    v.additional_jvm_args = [f"-D{loader['prefix']}.fixPackageAccess=true"]
    v.additional_traits = ["noapplet"]
    return v


def generate_intermediary():
    ensure_component_dir(INTERMEDIARY_COMPONENT)
    recommended_versions = []

    index = load_upstream_json(META_DIR, "intermediary.json")

    for entry in index:
        version = entry["version"]
        if not has_minecraft_version(version):
            continue

        print(f"Processing intermediary {version}")
        try:
            v = process_intermediary_version(entry)
        except Exception as e:
            eprint(f"Failed to process intermediary {version}")
            eprint(f"Error is {e}")
            continue

        recommended_versions.append(version)
        v.write(os.path.join(LAUNCHER_DIR, INTERMEDIARY_COMPONENT, f"{v.version}.json"))

    package = MetaPackage(
        uid=INTERMEDIARY_COMPONENT, name="Calamus Intermediary Mappings"
    )
    package.recommended = recommended_versions
    package.description = (
        "Calamus intermediary mappings allow using Fabric and Quilt Loader with mods "
        "for older versions of Minecraft in a more compatible manner."
    )
    package.project_url = "https://ornithemc.net"
    package.authors = ["OrnitheMC"]
    package.write(os.path.join(LAUNCHER_DIR, INTERMEDIARY_COMPONENT, "package.json"))


def generate_loader(loader_type, loader):
    ensure_component_dir(loader["uid"])
    recommended_versions = []

    index = load_upstream_json(META_DIR, f"{loader_type}-loader.json")

    for entry in index:
        version = entry["version"]
        print(f"Processing {loader_type} loader {version}")
        try:
            v = process_loader_version(loader, entry)
        except Exception as e:
            eprint(f"Failed to process {loader_type} loader {version}")
            eprint(f"Error is {e}")
            continue

        if not recommended_versions and entry["stable"]:
            recommended_versions.append(version)

        v.write(os.path.join(LAUNCHER_DIR, loader["uid"], f"{v.version}.json"))

    package = MetaPackage(uid=loader["uid"], name=loader["name"])
    package.recommended = recommended_versions
    package.description = (
        "Ornithe is a project bringing modern modding tooling to every version of "
        "Minecraft."
    )
    package.project_url = "https://ornithemc.net"
    package.authors = ["OrnitheMC"]
    package.write(os.path.join(LAUNCHER_DIR, loader["uid"], "package.json"))


def main():
    generate_intermediary()
    for loader_type, loader in LOADERS.items():
        generate_loader(loader_type, loader)


if __name__ == "__main__":
    main()
