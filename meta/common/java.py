from os.path import join

BASE_DIR = "java_runtime"

RELEASE_FILE = join(BASE_DIR, "releases.json")
ADOPTIUM_DIR = join(BASE_DIR, "adoptium")
AZUL_DIR = join(BASE_DIR, "azul")

ADOPTIUM_VERSIONS_DIR = join(ADOPTIUM_DIR, "versions")
AZUL_VERSIONS_DIR = join(AZUL_DIR, "versions")

JAVA_COMPONENT = "net.minecraft.java"