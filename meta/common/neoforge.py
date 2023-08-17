from os.path import join

from ..model import GradleSpecifier, make_launcher_library

BASE_DIR = "neoforge"

JARS_DIR = join(BASE_DIR, "jars")
INSTALLER_INFO_DIR = join(BASE_DIR, "installer_info")
INSTALLER_MANIFEST_DIR = join(BASE_DIR, "installer_manifests")
VERSION_MANIFEST_DIR = join(BASE_DIR, "version_manifests")
FILE_MANIFEST_DIR = join(BASE_DIR, "files_manifests")
DERIVED_INDEX_FILE = join(BASE_DIR, "derived_index.json")

NEOFORGE_COMPONENT = "net.neoforged"

FORGEWRAPPER_LIBRARY = make_launcher_library(
    GradleSpecifier("io.github.zekerzhayard", "ForgeWrapper", "1.5.6-prism"),
    "b059aa8c4d2508055c6ed2a2561923a5e670a5eb",
    34860,
)
