from os.path import join

BASE_DIR = "java_runtime"

RELEASE_FILE = join(BASE_DIR, "releases.json")
ADOPTIUM_DIR = join(BASE_DIR, "adoptium")
OPENJ9_DIR = join(BASE_DIR, "ibm")
AZUL_DIR = join(BASE_DIR, "azul")

ADOPTIUM_VERSIONS_DIR = join(ADOPTIUM_DIR, "versions")
OPENJ9_VERSIONS_DIR = join(OPENJ9_DIR, "versions")
AZUL_VERSIONS_DIR = join(AZUL_DIR, "versions")

JAVA_MINECRAFT_COMPONENT = "net.minecraft.java"
JAVA_ADOPTIUM_COMPONENT = "net.adoptium.java"
JAVA_OPENJ9_COMPONENT = "com.ibm.java"
JAVA_AZUL_COMPONENT = "com.azul.java"
