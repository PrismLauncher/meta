from os.path import join

BASE_DIR = "neoforge"

JARS_DIR = join(BASE_DIR, "jars")
INSTALLER_INFO_DIR = join(BASE_DIR, "installer_info")
INSTALLER_MANIFEST_DIR = join(BASE_DIR, "installer_manifests")
VERSION_MANIFEST_DIR = join(BASE_DIR, "version_manifests")
FILE_MANIFEST_DIR = join(BASE_DIR, "files_manifests")
DERIVED_INDEX_FILE = join(BASE_DIR, "derived_index.json")

STATIC_LEGACYINFO_FILE = join(BASE_DIR, "neoforge-legacyinfo.json")

NEOFORGE_COMPONENT = "net.neoforged"

FORGEWRAPPER_MAVEN = "https://github.com/ZekerZhayard/ForgeWrapper/releases/download/1.5.6/ForgeWrapper-1.5.6.jar"
BAD_VERSIONS = [""]
