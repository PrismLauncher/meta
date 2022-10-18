from os.path import join

BASE_DIR = "forge"

JARS_DIR = join(BASE_DIR, "jars")
INSTALLER_INFO_DIR = join(BASE_DIR, "installer_info")
INSTALLER_MANIFEST_DIR = join(BASE_DIR, "installer_manifests")
VERSION_MANIFEST_DIR = join(BASE_DIR, "version_manifests")
FILE_MANIFEST_DIR = join(BASE_DIR, "files_manifests")
DERIVED_INDEX_FILE = join(BASE_DIR, "derived_index.json")

STATIC_LEGACYINFO_FILE = join(BASE_DIR, "forge-legacyinfo.json")

FORGE_COMPONENT = "net.minecraftforge"

FORGEWRAPPER_MAVEN = "https://files.prismlauncher.org/maven/%s"
BAD_VERSIONS = ["1.12.2-14.23.5.2851"]
