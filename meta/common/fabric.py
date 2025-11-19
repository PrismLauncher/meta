from os.path import join

BASE_DIR = "fabric"

JARS_DIR = join(BASE_DIR, "jars")
INSTALLER_INFO_DIR = join(BASE_DIR, "loader-installer-json")
META_DIR = join(BASE_DIR, "meta-v2")

LOADER_COMPONENT = "net.fabricmc.fabric-loader"
INTERMEDIARY_COMPONENT = "net.fabricmc.intermediary"

DATETIME_FORMAT_HTTP = "%a, %d %b %Y %H:%M:%S %Z"

# version -> releaseTime
BROKEN_INTERMEDIARIES = {
    "1.21.11-pre1_unobfuscated": "2025-11-19T11:03:07+00:00"  # releaseTime of 1.21.11 intermediary
}
EARLY_UNOBFUSCATED_SUFFIX = "_unobfuscated"
NOOP_INTERMEDIARY_VERSION = "net.fabricmc:intermediary:0.0.0"
