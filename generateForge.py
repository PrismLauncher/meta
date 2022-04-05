import os
import re
import sys
from distutils.version import LooseVersion

from meta.common import ensure_component_dir, polymc_path, upstream_path, static_path
from meta.common.forge import FORGE_COMPONENT, INSTALLER_MANIFEST_DIR, VERSION_MANIFEST_DIR, DERIVED_INDEX_FILE, \
    STATIC_LEGACYINFO_FILE, INSTALLER_INFO_DIR, BAD_VERSIONS, FORGEWRAPPER_MAVEN
from meta.common.mojang import MINECRAFT_COMPONENT
from meta.model import MetaVersion, Dependency, Library, GradleSpecifier, MojangLibraryDownloads, MojangArtifact, \
    MetaPackage
from meta.model.forge import ForgeVersion, ForgeInstallerProfile, ForgeLegacyInfo, fml_libs_for_version, \
    ForgeInstallerProfileV2, InstallerInfo, DerivedForgeIndex, ForgeLegacyInfoList
from meta.model.mojang import MojangVersion

PMC_DIR = polymc_path()
UPSTREAM_DIR = upstream_path()
STATIC_DIR = static_path()

ensure_component_dir(FORGE_COMPONENT)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# Contruct a set of libraries out of a Minecraft version file, for filtering.
mcVersionCache = {}


def loadMcVersionFilter(version):
    if version in mcVersionCache:
        return mcVersionCache[version]
    libSet = set()
    mcVersion = MetaVersion.parse_file(os.path.join(PMC_DIR, MINECRAFT_COMPONENT, f"{version}.json"))
    for lib in mcVersion.libraries:
        libSet.add(lib.name)
    mcVersionCache[version] = libSet
    return libSet


'''
Match a library coordinate to a set of library coordinates.
 * Block those that pass completely.
 * For others, block those with lower versions than in the set.
'''


def shouldIgnoreArtifact(libSet, match):
    for ver in libSet:
        if ver.group == match.group and ver.artifact == match.artifact and ver.classifier == match.classifier:
            if ver.version == match.version:
                # Everything is matched perfectly - this one will be ignored
                return True
            else:
                # We say the lib matches (is the same) also when the new version is lower than the old one
                if LooseVersion(ver.version) > LooseVersion(match.version):
                    # eprint ("Lower version on %s:%s:%s: OLD=%s NEW=%s" % (ver.group, ver.artifact, ver.classifier, ver.version, match.version))
                    return True
                # Otherwise it did not match - new version is higher and this is an upgrade
                return False
    # No match found in the set - we need to keep this
    return False


def versionFromProfile(profile: ForgeInstallerProfile, version):
    result = MetaVersion(name="Forge", version=version.rawVersion, uid=FORGE_COMPONENT)
    mcversion = profile.install.minecraft
    result.requires = [Dependency(uid=MINECRAFT_COMPONENT, equals=mcversion)]
    result.main_class = profile.versionInfo.main_class
    args = profile.versionInfo.minecraft_arguments
    tweakers = []
    expression = re.compile("--tweakClass ([a-zA-Z0-9\\.]+)")
    match = expression.search(args)
    while match is not None:
        tweakers.append(match.group(1))
        args = args[:match.start()] + args[match.end():]
        match = expression.search(args)
    if len(tweakers) > 0:
        args = args.strip()
        result.additional_tweakers = tweakers
    # result.minecraftArguments = args
    result.release_time = profile.versionInfo.time
    libs = []
    mcFilter = loadMcVersionFilter(mcversion)
    for forgeLib in profile.versionInfo.libraries:
        if forgeLib.name.is_lwjgl():
            continue
        if forgeLib.name.is_log4j():
            continue
        if shouldIgnoreArtifact(mcFilter, forgeLib.name):
            continue
        fixedName = forgeLib.name
        if fixedName.group == "net.minecraftforge":
            if fixedName.artifact == "minecraftforge":
                fixedName.artifact = "forge"
                fixedName.classifier = "universal"
                fixedName.version = "%s-%s" % (mcversion, fixedName.version)
            elif fixedName.artifact == "forge":
                fixedName.classifier = "universal"
        ourLib = Library(name=fixedName)
        if forgeLib.url == "http://files.minecraftforge.net/maven/":
            ourLib.url = "https://maven.minecraftforge.net/"
        else:
            ourLib.url = forgeLib.url
        # if forgeLib.checksums and len(forgeLib.checksums) == 2:
        #    ourLib.mmcHint = "forge-pack-xz"
        libs.append(ourLib)
    result.libraries = libs
    result.order = 5
    return result


def versionFromModernizedInstaller(installerVersion: MojangVersion, version: ForgeVersion):
    eprint("Generating Modernized Forge %s." % version.longVersion)
    result = MetaVersion(name="Forge", version=version.rawVersion, uid=FORGE_COMPONENT)
    mcversion = version.mcversion
    result.requires = [Dependency(uid=MINECRAFT_COMPONENT, equals=mcversion)]
    result.main_class = installerVersion.main_class
    args = installerVersion.minecraft_arguments
    tweakers = []
    expression = re.compile("--tweakClass ([a-zA-Z0-9\\.]+)")
    match = expression.search(args)
    while match is not None:
        tweakers.append(match.group(1))
        args = args[:match.start()] + args[match.end():]
        match = expression.search(args)
    if len(tweakers) > 0:
        args = args.strip()
        result.additional_tweakers = tweakers
    # result.minecraftArguments = args
    result.release_time = installerVersion.release_time
    libs = []
    mcFilter = loadMcVersionFilter(mcversion)
    for upstreamLib in installerVersion.libraries:
        pmcLib = Library.parse_obj(upstreamLib.dict())
        if pmcLib.name.is_lwjgl():
            continue
        if pmcLib.name.is_log4j():
            continue
        if shouldIgnoreArtifact(mcFilter, pmcLib.name):
            continue
        if pmcLib.name.group == "net.minecraftforge":
            if pmcLib.name.artifact == "forge":
                fixedName = pmcLib.name
                fixedName.classifier = "universal"
                pmcLib.downloads.artifact.path = fixedName.path()
                pmcLib.downloads.artifact.url = "https://files.minecraftforge.net/maven/%s" % fixedName.path()
                pmcLib.name = fixedName
                libs.append(pmcLib)
                continue
            elif pmcLib.name.artifact == "minecraftforge":
                fixedName = pmcLib.name
                fixedName.artifact = "forge"
                fixedName.classifier = "universal"
                fixedName.version = "%s-%s" % (mcversion, fixedName.version)
                pmcLib.downloads.artifact.path = fixedName.path()
                pmcLib.downloads.artifact.url = "https://files.minecraftforge.net/maven/%s" % fixedName.path()
                pmcLib.name = fixedName
                libs.append(pmcLib)
                continue
        libs.append(pmcLib)

    result.libraries = libs
    result.order = 5
    return result


def versionFromLegacy(version: ForgeVersion, legacyinfo: ForgeLegacyInfo):
    result = MetaVersion(name="Forge", version=version.rawVersion, uid=FORGE_COMPONENT)
    mcversion = version.mcversion_sane
    result.requires = [Dependency(uid=MINECRAFT_COMPONENT, equals=mcversion)]
    result.release_time = legacyinfo.releaseTime
    result.order = 5
    if fml_libs_for_version(mcversion):  # WHY, WHY DID I WASTE MY TIME REWRITING FMLLIBSMAPPING
        result.additional_traits = ["legacyFML"]
    url = version.url()
    if "universal" in url:
        classifier = "universal"
    else:
        classifier = "client"
    coord = GradleSpecifier("net.minecraftforge", "forge", version.longVersion, classifier)
    mainmod = Library(name=coord)
    mainmod.downloads = MojangLibraryDownloads()
    mainmod.downloads.artifact = MojangArtifact(url=version.url(), sha1=legacyinfo.sha1, size=legacyinfo.size)
    mainmod.downloads.artifact.path = None
    result.jar_mods = [mainmod]
    return result


def versionFromBuildSystemInstaller(installerVersion: MojangVersion, installerProfile: ForgeInstallerProfileV2,
                                    version: ForgeVersion):
    eprint("Generating Forge %s." % version.longVersion)
    result = MetaVersion(name="Forge", version=version.rawVersion, uid=FORGE_COMPONENT)
    result.requires = [Dependency(uid=MINECRAFT_COMPONENT, equals=version.mcversion_sane)]
    result.main_class = "io.github.zekerzhayard.forgewrapper.installer.Main"

    # FIXME: Add the size and hash here
    mavenLibs = []

    # load the locally cached installer file info and use it to add the installer entry in the json
    installerInfo = InstallerInfo.parse_file(
        os.path.join(UPSTREAM_DIR, INSTALLER_INFO_DIR, f"{version.longVersion}.json"))
    InstallerLib = Library(
        name=GradleSpecifier("net.minecraftforge", "forge", version.longVersion, "installer"))
    InstallerLib.downloads = MojangLibraryDownloads()
    InstallerLib.downloads.artifact = MojangArtifact(
        url="https://files.minecraftforge.net/maven/%s" % (InstallerLib.name.path()),
        sha1=installerInfo.sha1hash,
        size=installerInfo.size)
    mavenLibs.append(InstallerLib)

    for upstreamLib in installerProfile.libraries:
        pmcLib = Library.parse_obj(upstreamLib.dict())
        if pmcLib.name.group == "net.minecraftforge":
            if pmcLib.name.artifact == "forge":
                if pmcLib.name.classifier == "universal":
                    pmcLib.downloads.artifact.url = "https://files.minecraftforge.net/maven/%s" % pmcLib.name.path()
                    mavenLibs.append(pmcLib)
                    continue
        if pmcLib.name.is_log4j():
            continue
        mavenLibs.append(pmcLib)

    result.maven_files = mavenLibs

    libraries = []

    wrapperLib = Library(name=GradleSpecifier("io.github.zekerzhayard", "ForgeWrapper", "mmc2"))
    wrapperLib.downloads = MojangLibraryDownloads()
    wrapperLib.downloads.artifact = MojangArtifact(url=FORGEWRAPPER_MAVEN % (wrapperLib.name.path()),
                                                   sha1="4ee5f25cc9c7efbf54aff4c695da1054c1a1d7a3",
                                                   size=34444)
    libraries.append(wrapperLib)

    for upstreamLib in installerVersion.libraries:
        pmcLib = Library.parse_obj(upstreamLib.dict())
        if pmcLib.name.group == "net.minecraftforge":
            if pmcLib.name.artifact == "forge":
                fixedName = pmcLib.name
                fixedName.classifier = "launcher"
                pmcLib.downloads.artifact.path = fixedName.path()
                pmcLib.downloads.artifact.url = "https://files.minecraftforge.net/maven/%s" % fixedName.path()
                pmcLib.name = fixedName
                libraries.append(pmcLib)
                continue
        if pmcLib.name.is_log4j():
            continue
        libraries.append(pmcLib)
    result.libraries = libraries

    result.release_time = installerVersion.release_time
    result.order = 5
    mcArgs = "--username ${auth_player_name} --version ${version_name} --gameDir ${game_directory} --assetsDir ${assets_root} --assetIndex ${assets_index_name} --uuid ${auth_uuid} --accessToken ${auth_access_token} --userType ${user_type} --versionType ${version_type}"
    for arg in installerVersion.arguments.game:
        mcArgs += " %s" % arg
    result.minecraft_arguments = mcArgs
    return result


def main():
    # load the locally cached version list
    remoteVersionlist = DerivedForgeIndex.parse_file(os.path.join(UPSTREAM_DIR, DERIVED_INDEX_FILE))

    recommendedVersions = []

    legacyinfolist = ForgeLegacyInfoList.parse_file(os.path.join(STATIC_DIR, STATIC_LEGACYINFO_FILE))

    legacyVersions = [
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

    for id, entry in remoteVersionlist.versions.items():
        if entry.mcversion is None:
            eprint("Skipping %s with invalid MC version" % id)
            continue

        version = ForgeVersion(entry)

        if version.longVersion in BAD_VERSIONS:
            # Version 1.12.2-14.23.5.2851 is ultra cringe, I can't imagine why you would even spend one second on
            # actually adding support for this version.
            # It is cringe, because it's installer info is broken af
            eprint(f"Skipping bad version {version.longVersion}")
            continue

        if version.url() is None:
            eprint("Skipping %s with no valid files" % id)
            continue
        eprint("Processing Forge %s" % version.rawVersion)
        versionElements = version.rawVersion.split('.')
        if len(versionElements) < 1:
            eprint("Skipping version %s with not enough version elements" % (id))
            continue

        majorVersionStr = versionElements[0]
        if not majorVersionStr.isnumeric():
            eprint("Skipping version %s with non-numeric major version %s" % (id, majorVersionStr))
            continue

        majorVersion = int(majorVersionStr)
        # if majorVersion >= 37:
        #    eprint ("Skipping unsupported major version %d (%s)" % (majorVersion, id))
        #    continue

        if entry.recommended:
            recommendedVersions.append(version.rawVersion)

        # If we do not have the corresponding Minecraft version, we ignore it
        if not os.path.isfile(os.path.join(PMC_DIR, MINECRAFT_COMPONENT, f"{version.mcversion_sane}.json")):
            eprint("Skipping %s with no corresponding Minecraft version %s" % (id, version.mcversion_sane))
            continue

        outVersion = None

        # Path for new-style build system based installers
        installerVersionFilepath = os.path.join(UPSTREAM_DIR, VERSION_MANIFEST_DIR, f"{version.longVersion}.json")
        profileFilepath = os.path.join(UPSTREAM_DIR, INSTALLER_MANIFEST_DIR, f"{version.longVersion}.json")

        eprint(installerVersionFilepath)
        if os.path.isfile(installerVersionFilepath):
            installerVersion = MojangVersion.parse_file(installerVersionFilepath)
            if entry.mcversion in legacyVersions:
                outVersion = versionFromModernizedInstaller(installerVersion, version)
            else:
                installerProfile = ForgeInstallerProfileV2.parse_file(profileFilepath)
                outVersion = versionFromBuildSystemInstaller(installerVersion, installerProfile, version)
        else:
            if version.uses_installer():

                # If we do not have the Forge json, we ignore this version
                if not os.path.isfile(profileFilepath):
                    eprint("Skipping %s with missing profile json" % id)
                    continue
                profile = ForgeInstallerProfile.parse_file(profileFilepath)
                outVersion = versionFromProfile(profile, version)
            else:
                # Generate json for legacy here
                if version.mcversion_sane == "1.6.1":
                    continue
                build = version.build
                if not str(build).encode('utf-8').decode('utf8') in legacyinfolist.number:
                    eprint("Legacy build %d is missing in legacy info. Ignoring." % build)
                    continue

                outVersion = versionFromLegacy(version, legacyinfolist.number[str(build)])

        outFilepath = os.path.join(PMC_DIR, FORGE_COMPONENT, f"{outVersion.version}.json")
        outVersion.write(outFilepath)

        recommendedVersions.sort()

        print('Recommended versions:', recommendedVersions)

        package = MetaPackage(uid=FORGE_COMPONENT, name="Forge", project_url="https://www.minecraftforge.net/forum/")
        package.recommended = recommendedVersions
        package.write(os.path.join(PMC_DIR, FORGE_COMPONENT, "package.json"))


if __name__ == '__main__':
    main()
