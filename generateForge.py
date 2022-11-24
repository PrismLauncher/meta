import os
import re
import sys
from distutils.version import LooseVersion
from operator import attrgetter
from typing import Collection

from meta.common import ensure_component_dir, launcher_path, upstream_path, static_path
from meta.common.forge import FORGE_COMPONENT, INSTALLER_MANIFEST_DIR, VERSION_MANIFEST_DIR, DERIVED_INDEX_FILE, \
    STATIC_LEGACYINFO_FILE, INSTALLER_INFO_DIR, BAD_VERSIONS, FORGEWRAPPER_MAVEN
from meta.common.mojang import MINECRAFT_COMPONENT
from meta.model import MetaVersion, Dependency, Library, GradleSpecifier, MojangLibraryDownloads, MojangArtifact, \
    MetaPackage
from meta.model.forge import ForgeVersion, ForgeInstallerProfile, ForgeLegacyInfo, fml_libs_for_version, \
    ForgeInstallerProfileV2, InstallerInfo, DerivedForgeIndex, ForgeLegacyInfoList
from meta.model.mojang import MojangVersion

LAUNCHER_DIR = launcher_path()
UPSTREAM_DIR = upstream_path()
STATIC_DIR = static_path()

ensure_component_dir(FORGE_COMPONENT)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# Construct a set of libraries out of a Minecraft version file, for filtering.
mc_version_cache = {}


def load_mc_version_filter(version: str):
    if version in mc_version_cache:
        return mc_version_cache[version]
    v = MetaVersion.parse_file(os.path.join(LAUNCHER_DIR, MINECRAFT_COMPONENT, f"{version}.json"))
    libs = set(map(attrgetter("name"), v.libraries))
    mc_version_cache[version] = libs
    return libs


'''
Match a library coordinate to a set of library coordinates.
 * Block those that pass completely.
 * For others, block those with lower versions than in the set.
'''


def should_ignore_artifact(libs: Collection[GradleSpecifier], match: GradleSpecifier):
    for ver in libs:
        if ver.group == match.group and ver.artifact == match.artifact and ver.classifier == match.classifier:
            if ver.version == match.version:
                # Everything is matched perfectly - this one will be ignored
                return True
            elif LooseVersion(ver.version) > LooseVersion(match.version):
                return True
            else:
                # Otherwise it did not match - new version is higher and this is an upgrade
                return False
    # No match found in the set - we need to keep this
    return False


def version_from_profile(profile: ForgeInstallerProfile, version: ForgeVersion) -> MetaVersion:
    v = MetaVersion(name="Forge", version=version.rawVersion, uid=FORGE_COMPONENT)
    mc_version = profile.install.minecraft
    v.requires = [Dependency(uid=MINECRAFT_COMPONENT, equals=mc_version)]
    v.main_class = profile.version_info.main_class
    v.release_time = profile.version_info.time

    args = profile.version_info.minecraft_arguments
    tweakers = []
    expression = re.compile(r"--tweakClass ([a-zA-Z0-9.]+)")
    match = expression.search(args)
    while match is not None:
        tweakers.append(match.group(1))
        args = args[:match.start()] + args[match.end():]
        match = expression.search(args)
    if len(tweakers) > 0:
        args = args.strip()
        v.additional_tweakers = tweakers
    # v.minecraftArguments = args

    v.libraries = []
    mc_filter = load_mc_version_filter(mc_version)
    for forge_lib in profile.version_info.libraries:
        if forge_lib.name.is_lwjgl() or forge_lib.name.is_log4j() or should_ignore_artifact(mc_filter, forge_lib.name):
            continue

        overridden_name = forge_lib.name
        if overridden_name.group == "net.minecraftforge":
            if overridden_name.artifact == "minecraftforge":
                overridden_name.artifact = "forge"
                overridden_name.version = "%s-%s" % (mc_version, overridden_name.version)

                overridden_name.classifier = "universal"
            elif overridden_name.artifact == "forge":
                overridden_name.classifier = "universal"

        overridden_lib = Library(name=overridden_name)
        if forge_lib.url == "http://maven.minecraftforge.net/":
            overridden_lib.url = "https://maven.minecraftforge.net/"
        else:
            overridden_lib.url = forge_lib.url
        # if forge_lib.checksums and len(forge_lib.checksums) == 2:
        #    overridden_lib.mmcHint = "forge-pack-xz"
        v.libraries.append(overridden_lib)

    v.order = 5
    return v


def version_from_modernized_installer(installer: MojangVersion, version: ForgeVersion) -> MetaVersion:
    v = MetaVersion(name="Forge", version=version.rawVersion, uid=FORGE_COMPONENT)
    mc_version = version.mc_version
    v.requires = [Dependency(uid=MINECRAFT_COMPONENT, equals=mc_version)]
    v.main_class = installer.main_class
    v.release_time = installer.release_time

    args = installer.minecraft_arguments
    tweakers = []
    expression = re.compile("--tweakClass ([a-zA-Z0-9.]+)")
    match = expression.search(args)
    while match is not None:
        tweakers.append(match.group(1))
        args = args[:match.start()] + args[match.end():]
        match = expression.search(args)
    if len(tweakers) > 0:
        args = args.strip()
        v.additional_tweakers = tweakers
    # v.minecraftArguments = args

    v.libraries = []

    mc_filter = load_mc_version_filter(mc_version)
    for upstream_lib in installer.libraries:
        forge_lib = Library.parse_obj(upstream_lib.dict())  # "cast" MojangLibrary to Library
        if forge_lib.name.is_lwjgl() or forge_lib.name.is_log4j() or should_ignore_artifact(mc_filter, forge_lib.name):
            continue

        if forge_lib.name.group == "net.minecraftforge":
            if forge_lib.name.artifact == "forge":
                overridden_name = forge_lib.name
                overridden_name.classifier = "universal"
                forge_lib.downloads.artifact.path = overridden_name.path()
                forge_lib.downloads.artifact.url = "https://maven.minecraftforge.net/%s" % overridden_name.path()
                forge_lib.name = overridden_name

            elif forge_lib.name.artifact == "minecraftforge":
                overridden_name = forge_lib.name
                overridden_name.artifact = "forge"
                overridden_name.classifier = "universal"
                overridden_name.version = "%s-%s" % (mc_version, overridden_name.version)
                forge_lib.downloads.artifact.path = overridden_name.path()
                forge_lib.downloads.artifact.url = "https://maven.minecraftforge.net/%s" % overridden_name.path()
                forge_lib.name = overridden_name

        v.libraries.append(forge_lib)

    v.order = 5
    return v


def version_from_legacy(info: ForgeLegacyInfo, version: ForgeVersion) -> MetaVersion:
    v = MetaVersion(name="Forge", version=version.rawVersion, uid=FORGE_COMPONENT)
    mc_version = version.mc_version_sane
    v.requires = [Dependency(uid=MINECRAFT_COMPONENT, equals=mc_version)]
    v.release_time = info.release_time
    v.order = 5
    if fml_libs_for_version(mc_version):  # WHY, WHY DID I WASTE MY TIME REWRITING FMLLIBSMAPPING
        v.additional_traits = ["legacyFML"]

    classifier = "client"
    if "universal" in version.url():
        classifier = "universal"

    main_mod = Library(name=GradleSpecifier("net.minecraftforge", "forge", version.long_version, classifier))
    main_mod.downloads = MojangLibraryDownloads()
    main_mod.downloads.artifact = MojangArtifact(url=version.url(), sha1=info.sha1, size=info.size)
    main_mod.downloads.artifact.path = None
    v.jar_mods = [main_mod]
    return v


def version_from_build_system_installer(installer: MojangVersion, profile: ForgeInstallerProfileV2,
                                        version: ForgeVersion) -> MetaVersion:
    v = MetaVersion(name="Forge", version=version.rawVersion, uid=FORGE_COMPONENT)
    v.requires = [Dependency(uid=MINECRAFT_COMPONENT, equals=version.mc_version_sane)]
    v.main_class = "io.github.zekerzhayard.forgewrapper.installer.Main"

    # FIXME: Add the size and hash here
    v.maven_files = []

    # load the locally cached installer file info and use it to add the installer entry in the json
    info = InstallerInfo.parse_file(
        os.path.join(UPSTREAM_DIR, INSTALLER_INFO_DIR, f"{version.long_version}.json"))
    installer_lib = Library(
        name=GradleSpecifier("net.minecraftforge", "forge", version.long_version, "installer"))
    installer_lib.downloads = MojangLibraryDownloads()
    installer_lib.downloads.artifact = MojangArtifact(
        url="https://maven.minecraftforge.net/%s" % (installer_lib.name.path()),
        sha1=info.sha1hash,
        size=info.size)
    v.maven_files.append(installer_lib)

    for upstream_lib in profile.libraries:
        forge_lib = Library.parse_obj(upstream_lib.dict())
        if forge_lib.name.is_log4j():
            continue

        if forge_lib.name.group == "net.minecraftforge" and forge_lib.name.artifact == "forge" \
                and forge_lib.name.classifier == "universal":
            forge_lib.downloads.artifact.url = "https://maven.minecraftforge.net/%s" % forge_lib.name.path()
        v.maven_files.append(forge_lib)

    v.libraries = []

    wrapper_lib = Library(name=GradleSpecifier("io.github.zekerzhayard", "ForgeWrapper", "mmc2"))
    wrapper_lib.downloads = MojangLibraryDownloads()
    wrapper_lib.downloads.artifact = MojangArtifact(url=FORGEWRAPPER_MAVEN % (wrapper_lib.name.path()),
                                                    sha1="4ee5f25cc9c7efbf54aff4c695da1054c1a1d7a3",
                                                    size=34444)
    v.libraries.append(wrapper_lib)

    for upstream_lib in installer.libraries:
        forge_lib = Library.parse_obj(upstream_lib.dict())
        if forge_lib.name.is_log4j():
            continue

        if forge_lib.name.group == "net.minecraftforge":
            if forge_lib.name.artifact == "forge":
                forge_lib.name.classifier = "launcher"
                forge_lib.downloads.artifact.path = forge_lib.name.path()
                forge_lib.downloads.artifact.url = "https://maven.minecraftforge.net/%s" % forge_lib.name.path()
                forge_lib.name = forge_lib.name
        v.libraries.append(forge_lib)

    v.release_time = installer.release_time
    v.order = 5
    mc_args = "--username ${auth_player_name} --version ${version_name} --gameDir ${game_directory} " \
              "--assetsDir ${assets_root} --assetIndex ${assets_index_name} --uuid ${auth_uuid} " \
              "--accessToken ${auth_access_token} --userType ${user_type} --versionType ${version_type}"
    for arg in installer.arguments.game:
        mc_args += f" {arg}"
    v.minecraft_arguments = mc_args
    return v


def main():
    # load the locally cached version list
    remote_versions = DerivedForgeIndex.parse_file(os.path.join(UPSTREAM_DIR, DERIVED_INDEX_FILE))
    recommended_versions = []

    legacy_info_list = ForgeLegacyInfoList.parse_file(os.path.join(STATIC_DIR, STATIC_LEGACYINFO_FILE))
    legacy_versions = [
        "1.1",
        "1.2.3",
        "1.2.4",
        "1.2.5",
        "1.3.2",
        "1.4.1",
        "1.4.2",
        "1.4.3",
        "1.4.4",
        "1.4.5",
        "1.4.6",
        "1.4.7",
        "1.5",
        "1.5.1",
        "1.5.2",
        "1.6.1",
        "1.6.2",
        "1.6.3",
        "1.6.4",
        "1.7.10",
        "1.7.10-pre4",
        "1.7.2",
        "1.8",
        "1.8.8",
        "1.8.9",
        "1.9",
        "1.9.4",
        "1.10",
        "1.10.2",
        "1.11",
        "1.11.2",
        "1.12",
        "1.12.1",
        "1.12.2",
    ]

    for key, entry in remote_versions.versions.items():
        if entry.mc_version is None:
            eprint("Skipping %s with invalid MC version" % key)
            continue

        version = ForgeVersion(entry)

        if version.long_version in BAD_VERSIONS:
            # Version 1.12.2-14.23.5.2851 is ultra cringe, I can't imagine why you would even spend one second on
            # actually adding support for this version.
            # It is cringe, because it's installer info is broken af
            eprint(f"Skipping bad version {version.long_version}")
            continue

        if version.url() is None:
            eprint("Skipping %s with no valid files" % key)
            continue
        eprint("Processing Forge %s" % version.rawVersion)
        version_elements = version.rawVersion.split('.')
        if len(version_elements) < 1:
            eprint("Skipping version %s with not enough version elements" % key)
            continue

        major_version_str = version_elements[0]
        if not major_version_str.isnumeric():
            eprint("Skipping version %s with non-numeric major version %s" % (key, major_version_str))
            continue

        if entry.recommended:
            recommended_versions.append(version.rawVersion)

        # If we do not have the corresponding Minecraft version, we ignore it
        if not os.path.isfile(os.path.join(LAUNCHER_DIR, MINECRAFT_COMPONENT, f"{version.mc_version_sane}.json")):
            eprint("Skipping %s with no corresponding Minecraft version %s" % (key, version.mc_version_sane))
            continue

        # Path for new-style build system based installers
        installer_version_filepath = os.path.join(UPSTREAM_DIR, VERSION_MANIFEST_DIR, f"{version.long_version}.json")
        profile_filepath = os.path.join(UPSTREAM_DIR, INSTALLER_MANIFEST_DIR, f"{version.long_version}.json")

        eprint(installer_version_filepath)
        if os.path.isfile(installer_version_filepath):
            installer = MojangVersion.parse_file(installer_version_filepath)
            if entry.mc_version in legacy_versions:
                v = version_from_modernized_installer(installer, version)
            else:
                profile = ForgeInstallerProfileV2.parse_file(profile_filepath)
                v = version_from_build_system_installer(installer, profile, version)
        else:
            if version.uses_installer():

                # If we do not have the Forge json, we ignore this version
                if not os.path.isfile(profile_filepath):
                    eprint("Skipping %s with missing profile json" % key)
                    continue
                profile = ForgeInstallerProfile.parse_file(profile_filepath)
                v = version_from_profile(profile, version)
            else:
                # Generate json for legacy here
                if version.mc_version_sane == "1.6.1":
                    continue
                build = version.build
                if not str(build).encode('utf-8').decode('utf8') in legacy_info_list.number:
                    eprint("Legacy build %d is missing in legacy info. Ignoring." % build)
                    continue

                v = version_from_legacy(legacy_info_list.number[str(build)], version)

        v.write(os.path.join(LAUNCHER_DIR, FORGE_COMPONENT, f"{v.version}.json"))

        recommended_versions.sort()

        print('Recommended versions:', recommended_versions)

        package = MetaPackage(uid=FORGE_COMPONENT, name="Forge", project_url="https://www.minecraftforge.net/forum/")
        package.recommended = recommended_versions
        package.write(os.path.join(LAUNCHER_DIR, FORGE_COMPONENT, "package.json"))


if __name__ == '__main__':
    main()
