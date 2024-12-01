from os.path import join, dirname

BASE_DIR = "omniarchive"

VERSION_MANIFEST_FILE = join(BASE_DIR, "omnifest_v0_real.json")
VERSIONS_DIR = join(BASE_DIR, "versions")
ASSETS_DIR = join(BASE_DIR, "assets")

STATIC_LEGACY_SERVICES_FILE = join(
    dirname(__file__), "omniarchive-minecraft-legacy-services.json"
)
LIBRARY_PATCHES_FILE = join(dirname(__file__), "mojang-library-patches.json")

MINECRAFT_COMPONENT = "net.minecraft"
LWJGL_COMPONENT = "org.lwjgl"
LWJGL3_COMPONENT = "org.lwjgl3"

JAVA_MANIFEST_FILE = join(BASE_DIR, "omniarchive_all.json")
