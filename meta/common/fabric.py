from os.path import join

BASE_DIR = "fabric"

JARS_DIR = join(BASE_DIR, "jars")
INSTALLER_INFO_DIR = join(BASE_DIR, "loader-installer-json")
META_DIR = join(BASE_DIR, "meta-v2")

LOADER_COMPONENT = "net.fabricmc.fabric-loader"
INTERMEDIARY_COMPONENT = "net.fabricmc.intermediary"

DATETIME_FORMAT_HTTP = "%a, %d %b %Y %H:%M:%S %Z"
