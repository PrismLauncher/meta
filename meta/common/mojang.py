from os.path import join

BASE_DIR = "mojang"

VERSION_MANIFEST_FILE = join(BASE_DIR, "version_manifest_v2.json")
VERSIONS_DIR = join(BASE_DIR, "versions")
ASSETS_DIR = join(BASE_DIR, "assets")

STATIC_EXPERIMENTS_FILE = join(BASE_DIR, "minecraft-experiments.json")
STATIC_OLD_SNAPSHOTS_FILE = join(BASE_DIR, "minecraft-old-snapshots.json")
STATIC_OVERRIDES_FILE = join(BASE_DIR, "minecraft-legacy-override.json")
LIBRARY_PATCHES_FILE = join(BASE_DIR, "library-patches.json")

MINECRAFT_COMPONENT = "net.minecraft"
LWJGL_COMPONENT = "org.lwjgl"
LWJGL3_COMPONENT = "org.lwjgl3"
