from os.path import join

BASE_DIR = "mojang"

VERSION_MANIFEST_FILE = join(BASE_DIR, "version_manifest_v2.json")
VERSIONS_DIR = join(BASE_DIR, "versions")
ASSETS_DIR = join(BASE_DIR, "assets")

STATIC_EXPERIMENTS_FILE = join(BASE_DIR, "minecraft-experiments.json")
STATIC_LWJGL322_FILE = join(BASE_DIR, "lwjgl-3.2.2.json")
STATIC_OVERRIDES_FILE = join(BASE_DIR, "minecraft-legacy-override.json")

MINECRAFT_COMPONENT = "net.minecraft"
LWJGL_COMPONENT = "org.lwjgl"
LWJGL3_COMPONENT = "org.lwjgl3"
