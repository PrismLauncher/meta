from os.path import join

from ..model import GradleSpecifier, make_launcher_library

BASE_DIR = "forge"

JARS_DIR = join(BASE_DIR, "jars")
INSTALLER_INFO_DIR = join(BASE_DIR, "installer_info")
INSTALLER_MANIFEST_DIR = join(BASE_DIR, "installer_manifests")
VERSION_MANIFEST_DIR = join(BASE_DIR, "version_manifests")
FILE_MANIFEST_DIR = join(BASE_DIR, "files_manifests")
DERIVED_INDEX_FILE = join(BASE_DIR, "derived_index.json")

STATIC_LEGACYINFO_FILE = join(BASE_DIR, "forge-legacyinfo.json")

FORGE_COMPONENT = "net.minecraftforge"

FORGEWRAPPER_LIBRARY = make_launcher_library(
    GradleSpecifier("io.github.zekerzhayard", "ForgeWrapper", "mmc2"),
    "4ee5f25cc9c7efbf54aff4c695da1054c1a1d7a3",
    34444,
)
BAD_VERSIONS = ["1.12.2-14.23.5.2851"]
