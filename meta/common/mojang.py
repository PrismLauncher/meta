from os.path import join, dirname

BASE_DIR = "mojang"

VERSION_MANIFEST_FILE = join(BASE_DIR, "version_manifest_v2.json")
VERSIONS_DIR = join(BASE_DIR, "versions")
ASSETS_DIR = join(BASE_DIR, "assets")

STATIC_EXPERIMENTS_FILE = join(dirname(__file__), "mojang-minecraft-experiments.json")
STATIC_OLD_SNAPSHOTS_FILE = join(
    dirname(__file__), "mojang-minecraft-old-snapshots.json"
)
STATIC_OVERRIDES_FILE = join(dirname(__file__), "mojang-minecraft-legacy-override.json")
STATIC_LEGACY_SERVICES_FILE = join(
    dirname(__file__), "mojang-minecraft-legacy-services.json"
)
LIBRARY_PATCHES_FILE = join(dirname(__file__), "mojang-library-patches.json")

MINECRAFT_COMPONENT = "net.minecraft"
LWJGL_COMPONENT = "org.lwjgl"
LWJGL3_COMPONENT = "org.lwjgl3"
