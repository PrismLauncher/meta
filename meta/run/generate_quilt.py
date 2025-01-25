import json
import os
import sys

from meta.common import (
    ensure_component_dir,
    launcher_path,
    upstream_path,
    transform_maven_key,
)
from meta.common.quilt import (
    JARS_DIR,
    INSTALLER_INFO_DIR,
    META_DIR,
    INTERMEDIARY_COMPONENT,
    LOADER_COMPONENT,
    USE_QUILT_MAPPINGS,
    DISABLE_BEACON_ARG,
    DISABLE_BEACON_VERSIONS,
)
from meta.model import MetaVersion, Dependency, Library, MetaPackage, GradleSpecifier
from meta.model.fabric import FabricJarInfo, FabricInstallerDataV1, FabricMainClasses

LAUNCHER_DIR = launcher_path()
UPSTREAM_DIR = upstream_path()

ensure_component_dir(LOADER_COMPONENT)
ensure_component_dir(INTERMEDIARY_COMPONENT)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def load_jar_info(artifact_key) -> FabricJarInfo:
    return FabricJarInfo.parse_file(
        os.path.join(UPSTREAM_DIR, JARS_DIR, f"{artifact_key}.json")
    )


def load_installer_info(version) -> FabricInstallerDataV1:
    return FabricInstallerDataV1.parse_file(
        os.path.join(UPSTREAM_DIR, INSTALLER_INFO_DIR, f"{version}.json")
    )


def process_loader_version(entry) -> (MetaVersion, bool):
    should_recommend = (
        "-" not in entry["version"]
    )  # Don't recommend pre releases as per SemVer

    jar_info = load_jar_info(transform_maven_key(entry["maven"]))
    installer_info = load_installer_info(entry["version"])

    v = MetaVersion(name="Quilt Loader", uid=LOADER_COMPONENT, version=entry["version"])
    v.release_time = jar_info.release_time
    v.requires = [Dependency(uid=INTERMEDIARY_COMPONENT)]
    v.order = 10
    v.type = "release"
    if isinstance(installer_info.main_class, FabricMainClasses):
        v.main_class = installer_info.main_class.client
    else:
        v.main_class = installer_info.main_class
    v.libraries = []
    v.libraries.extend(installer_info.libraries.common)
    v.libraries.extend(installer_info.libraries.client)
    loader_lib = Library(
        name=GradleSpecifier.from_string(entry["maven"]),
        url="https://maven.quiltmc.org/repository/release",
    )
    v.libraries.append(loader_lib)

    if entry["version"] in DISABLE_BEACON_VERSIONS:
        if not v.additional_jvm_args:
            v.additional_jvm_args = []
        v.additional_jvm_args.append(DISABLE_BEACON_ARG)

    return v, should_recommend


def process_intermediary_version(entry) -> MetaVersion:
    jar_info = load_jar_info(transform_maven_key(entry["maven"]))

    v = MetaVersion(
        name="Quilt Intermediary Mappings",
        uid=INTERMEDIARY_COMPONENT,
        version=entry["version"],
    )
    v.release_time = jar_info.release_time
    v.requires = [Dependency(uid="net.minecraft", equals=entry["version"])]
    v.order = 11
    v.type = "release"
    v.libraries = []
    v.volatile = True
    intermediary_lib = Library(
        name=GradleSpecifier.from_string(entry["maven"]),
        url="https://maven.quiltmc.org/repository/release",
    )
    v.libraries.append(intermediary_lib)
    return v


def main():
    recommended_loader_versions = []
    recommended_intermediary_versions = []

    with open(
        os.path.join(UPSTREAM_DIR, META_DIR, "loader.json"), "r", encoding="utf-8"
    ) as f:
        loader_version_index = json.load(f)
        for entry in loader_version_index:
            version = entry["version"]
            print(f"Processing loader {version}")
            try:
                v, should_recommend = process_loader_version(entry)

                if (
                    not recommended_loader_versions and should_recommend
                ):  # newest stable loader is recommended
                    recommended_loader_versions.append(version)

                v.write(
                    os.path.join(LAUNCHER_DIR, LOADER_COMPONENT, f"{v.version}.json")
                )
            except Exception as e:
                eprint("Failed to download %s" % version)
                eprint("Error is %s" % e)
                continue

    if USE_QUILT_MAPPINGS:
        with open(
            os.path.join(UPSTREAM_DIR, META_DIR, "hashed.json"), "r", encoding="utf-8"
        ) as f:
            intermediary_version_index = json.load(f)
            for entry in intermediary_version_index:
                version = entry["version"]
                print(f"Processing intermediary {version}")

                try:
                    v = process_intermediary_version(entry)

                    recommended_intermediary_versions.append(
                        version
                    )  # all intermediaries are recommended

                    v.write(
                        os.path.join(
                            LAUNCHER_DIR, INTERMEDIARY_COMPONENT, f"{v.version}.json"
                        )
                    )
                except Exception as e:
                    eprint("Failed to download %s" % version)
                    eprint("Error is %s" % e)
                    continue
    package = MetaPackage(uid=LOADER_COMPONENT, name="Quilt Loader")
    package.recommended = recommended_loader_versions
    package.description = "The Quilt project is an open, community-driven modding toolchain designed primarily for Minecraft."
    package.project_url = "https://quiltmc.org/"
    package.authors = ["Quilt Project"]
    package.write(os.path.join(LAUNCHER_DIR, LOADER_COMPONENT, "package.json"))

    if USE_QUILT_MAPPINGS:
        package = MetaPackage(
            uid=INTERMEDIARY_COMPONENT, name="Quilt Intermediary Mappings"
        )
        package.recommended = recommended_intermediary_versions
        package.description = "Intermediary mappings allow using Quilt Loader with mods for Minecraft in a more compatible manner."
        package.project_url = "https://quiltmc.org/"
        package.authors = ["Quilt Project"]
        package.write(
            os.path.join(LAUNCHER_DIR, INTERMEDIARY_COMPONENT, "package.json")
        )


if __name__ == "__main__":
    main()
