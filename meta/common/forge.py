from os.path import join, dirname

from ..model import GradleSpecifier, make_launcher_library

BASE_DIR = "forge"

JARS_DIR = join(BASE_DIR, "jars")
INSTALLER_INFO_DIR = join(BASE_DIR, "installer_info")
INSTALLER_MANIFEST_DIR = join(BASE_DIR, "installer_manifests")
VERSION_MANIFEST_DIR = join(BASE_DIR, "version_manifests")
FILE_MANIFEST_DIR = join(BASE_DIR, "files_manifests")
DERIVED_INDEX_FILE = join(BASE_DIR, "derived_index.json")
LEGACYINFO_FILE = join(BASE_DIR, "legacyinfo.json")

FORGE_COMPONENT = "net.minecraftforge"

FORGEWRAPPER_LIBRARY = make_launcher_library(
    GradleSpecifier("io.github.zekerzhayard", "ForgeWrapper", "prism-2025-10-04"),
    "7dd8189b0a0d5cf951b4b26e22fb95776bd1dede",
    29187,
)
BAD_VERSIONS = ["1.12.2-14.23.5.2851"]
