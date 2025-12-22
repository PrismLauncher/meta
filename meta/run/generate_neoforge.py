from copy import deepcopy
import os
import re
import sys
from operator import attrgetter
from typing import Collection

from meta.common import ensure_component_dir, launcher_path, upstream_path
from meta.common.neoforge import (
    NEOFORGE_COMPONENT,
    INSTALLER_MANIFEST_DIR,
    VERSION_MANIFEST_DIR,
    DERIVED_INDEX_FILE,
    INSTALLER_INFO_DIR,
)
from meta.common.forge import FORGEWRAPPER_LIBRARY
from meta.common.mojang import MINECRAFT_COMPONENT
from meta.model import (
    MetaVersion,
    Dependency,
    Library,
    GradleSpecifier,
    MojangLibraryDownloads,
    MojangArtifact,
    MetaPackage,
)
from meta.model.neoforge import (
    NeoForgeVersion,
    NeoForgeInstallerProfileV2,
    InstallerInfo,
    DerivedNeoForgeIndex,
)
from meta.model.mojang import MojangVersion

LAUNCHER_DIR = launcher_path()
UPSTREAM_DIR = upstream_path()

ensure_component_dir(NEOFORGE_COMPONENT)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def version_from_build_system_installer(
    installer: MojangVersion,
    profile: NeoForgeInstallerProfileV2,
    version: NeoForgeVersion,
) -> MetaVersion:
    v = MetaVersion(name="NeoForge", version=version.rawVersion, uid=NEOFORGE_COMPONENT)
    v.main_class = "io.github.zekerzhayard.forgewrapper.installer.Main"

    # FIXME: Add the size and hash here
    v.maven_files = []

    # load the locally cached installer file info and use it to add the installer entry in the json
    info = InstallerInfo.parse_file(
        os.path.join(UPSTREAM_DIR, INSTALLER_INFO_DIR, f"{version.long_version}.json")
    )
    installer_lib = Library(
        name=GradleSpecifier(
            "net.neoforged", version.artifact, version.long_version, "installer"
        )
    )
    installer_lib.downloads = MojangLibraryDownloads()
    installer_lib.downloads.artifact = MojangArtifact(
        url="https://maven.neoforged.net/%s" % (installer_lib.name.path()),
        sha1=info.sha1hash,
        size=info.size,
    )
    v.maven_files.append(installer_lib)

    for forge_lib in profile.libraries:
        if forge_lib.name.is_log4j():
            continue

        v.maven_files.append(forge_lib)

    v.libraries = []

    v.libraries.append(FORGEWRAPPER_LIBRARY)

    for forge_lib in installer.libraries:
        if forge_lib.name.is_log4j():
            continue

        v.libraries.append(forge_lib)

    v.release_time = installer.release_time
    v.order = 5
    mc_args = (
        "--username ${auth_player_name} --version ${version_name} --gameDir ${game_directory} "
        "--assetsDir ${assets_root} --assetIndex ${assets_index_name} --uuid ${auth_uuid} "
        "--accessToken ${auth_access_token} --userType ${user_type} --versionType ${version_type}"
    )
    for arg in installer.arguments.game:
        mc_args += f" {arg}"
    v.minecraft_arguments = mc_args
    return v


def main():
    # load the locally cached version list
    remote_versions = DerivedNeoForgeIndex.parse_file(
        os.path.join(UPSTREAM_DIR, DERIVED_INDEX_FILE)
    )
    recommended_versions = []

    for key, entry in remote_versions.versions.items():
        version = NeoForgeVersion(entry)

        if version.url() is None:
            eprint("Skipping %s with no valid files" % key)
            continue
        eprint("Processing NeoForge %s" % version.rawVersion)
        version_elements = version.rawVersion.split(".")
        if len(version_elements) < 1:
            eprint("Skipping version %s with not enough version elements" % key)
            continue

        major_version_str = version_elements[0]
        if not major_version_str.isnumeric():
            eprint(
                "Skipping version %s with non-numeric major version %s"
                % (key, major_version_str)
            )
            continue

        if entry.recommended:
            recommended_versions.append(version.rawVersion)

        # Path for new-style build system based installers
        installer_version_filepath = os.path.join(
            UPSTREAM_DIR, VERSION_MANIFEST_DIR, f"{version.long_version}.json"
        )
        profile_filepath = os.path.join(
            UPSTREAM_DIR, INSTALLER_MANIFEST_DIR, f"{version.long_version}.json"
        )

        eprint(installer_version_filepath)
        assert os.path.isfile(
            installer_version_filepath
        ), f"version {installer_version_filepath} does not have installer version manifest"
        installer = MojangVersion.parse_file(installer_version_filepath)
        profile = NeoForgeInstallerProfileV2.parse_file(profile_filepath)
        v = version_from_build_system_installer(installer, profile, version)
        
        #we can get the minecraft version from the profile json info, so let's just do that instead of hacky regex
        v.requires = [Dependency(uid=MINECRAFT_COMPONENT, equals=profile.minecraft)] 
        # If we do not have the corresponding Minecraft version, we ignore it
        if not os.path.isfile(
            os.path.join(
                LAUNCHER_DIR, MINECRAFT_COMPONENT, f"{profile.minecraft}.json"
            )
        ):
            eprint(
                "Skipping %s with no corresponding Minecraft version %s"
                % (key, profile.minecraft)
            )
            continue     
        v.write(os.path.join(LAUNCHER_DIR, NEOFORGE_COMPONENT, f"{v.version}.json"))

        recommended_versions.sort()

        print("Recommended versions:", recommended_versions)

        package = MetaPackage(
            uid=NEOFORGE_COMPONENT,
            name="NeoForge",
            project_url="https://neoforged.net",
        )
        package.recommended = recommended_versions
        package.write(os.path.join(LAUNCHER_DIR, NEOFORGE_COMPONENT, "package.json"))


if __name__ == "__main__":
    main()
