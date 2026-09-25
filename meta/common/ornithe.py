from os.path import join

from . import fabric

BASE_DIR = "ornithe"

JARS_DIR = join(BASE_DIR, "jars")
LIBRARIES_DIR = join(BASE_DIR, "libraries")
LWJGL_DIR = join(BASE_DIR, "lwjgl")
META_DIR = join(BASE_DIR, "meta-v3")

META_URL = "https://meta.ornithemc.net/v3/versions"
MAVEN_URL = "https://maven.ornithemc.net/releases"
MC_VERSIONS_URL = "https://ornithemc.net/mc-versions"

LWJGL_MAVEN_HOST = "maven.legacyfabric.net"

INTERMEDIARY_GENERATION = 2

INTERMEDIARY_COMPONENT = "net.ornithemc.calamus-intermediary"

JAVA_MAJORS = [25, 21, 17, 8]
JAVA_NAME = "java-runtime-epsilon"

LOADERS = {
    "fabric": {
        "uid": "net.ornithemc.fabric-loader",
        "name": "Ornithe Fabric Loader",
        "prefix": "fabric",
        "maven": "https://maven.fabricmc.net",
        "jars_dir": fabric.JARS_DIR,
        "installer_info_dir": fabric.INSTALLER_INFO_DIR,
    },
}
