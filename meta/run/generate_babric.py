import json
import os
from datetime import datetime

from meta.common import (
    ensure_component_dir,
    launcher_path,
    upstream_path,
    transform_maven_key,
)
from meta.common.babric import (
    GLASS_MAVEN,
    JARS_DIR,
    META_DIR,
    LOADER_COMPONENT,
    INTERMEDIARY_COMPONENT,
)
from meta.model import MetaVersion, Dependency, Library, MetaPackage, GradleSpecifier
from meta.model.fabric import FabricJarInfo

LAUNCHER_DIR = launcher_path()
UPSTREAM_DIR = upstream_path()

ensure_component_dir(LOADER_COMPONENT)


def load_jar_info(artifact_key) -> FabricJarInfo:
    return FabricJarInfo.parse_file(
        os.path.join(UPSTREAM_DIR, JARS_DIR, f"{artifact_key}.json")
    )


def process_intermediary_version(entry, release_time: datetime) -> MetaVersion:
    v = MetaVersion(
        name="Intermediary Mappings",
        uid=INTERMEDIARY_COMPONENT,
        version=entry["version"],
    )
    v.release_time = release_time
    v.requires = [Dependency(uid="net.minecraft", equals=entry["version"])]
    v.order = 11
    v.type = "release"
    v.volatile = True
    v.libraries = [
        Library(
            name=GradleSpecifier.from_string(entry["maven"]),
            url=GLASS_MAVEN,
        )
    ]
    return v


def process_babric_version(mc_version: str, release_time: datetime) -> MetaVersion:
    v = MetaVersion(
        name="Babric",
        uid=LOADER_COMPONENT,
        version=mc_version,
    )
    v.release_time = release_time
    v.requires = [Dependency(uid="net.minecraft", equals=mc_version)]
    v.order = 10
    v.type = "release"
    v.additional_jvm_args = ["-DFabricMcEmu=net.minecraft.client.main.Main"]
    v.libraries = [
        Library(
            name=GradleSpecifier.from_string("babric:log4j-config:1.0.0"),
            url=GLASS_MAVEN,
        )
    ]
    return v


def ensure_intermediary_package():
    """Create a minimal package.json for net.fabricmc.intermediary if fabric hasn't done so yet."""
    package_path = os.path.join(LAUNCHER_DIR, INTERMEDIARY_COMPONENT, "package.json")
    if not os.path.exists(package_path):
        ensure_component_dir(INTERMEDIARY_COMPONENT)
        package = MetaPackage(uid=INTERMEDIARY_COMPONENT, name="Intermediary Mappings")
        package.recommended = []
        package.description = (
            "Intermediary mappings allow using Fabric Loader with mods for Minecraft "
            "in a more compatible manner."
        )
        package.project_url = "https://fabricmc.net"
        package.authors = ["Fabric Developers"]
        package.write(package_path)


def main():
    recommended_babric_versions = []

    with open(
        os.path.join(UPSTREAM_DIR, META_DIR, "intermediary.json"), "r", encoding="utf-8"
    ) as f:
        intermediary_index = json.load(f)

    ensure_intermediary_package()

    for entry in intermediary_index:
        mc_version = entry["version"]
        print(f"Processing Babric for Minecraft {mc_version}")

        jar_info = load_jar_info(transform_maven_key(entry["maven"]))
        release_time = jar_info.release_time

        intermediary = process_intermediary_version(entry, release_time)
        intermediary.write(
            os.path.join(LAUNCHER_DIR, INTERMEDIARY_COMPONENT, f"{mc_version}.json")
        )

        babric = process_babric_version(mc_version, release_time)
        babric.write(
            os.path.join(LAUNCHER_DIR, LOADER_COMPONENT, f"{mc_version}.json")
        )

        if entry.get("stable", True):
            recommended_babric_versions.append(mc_version)

    package = MetaPackage(uid=LOADER_COMPONENT, name="Babric")
    package.recommended = recommended_babric_versions
    package.description = (
        "Babric is a Fabric-based mod loader for Minecraft Beta 1.7.3."
    )
    package.project_url = "https://github.com/babric"
    package.authors = ["Babric Contributors"]
    package.write(os.path.join(LAUNCHER_DIR, LOADER_COMPONENT, "package.json"))


if __name__ == "__main__":
    main()
