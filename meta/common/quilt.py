from os.path import join
from .fabric import INTERMEDIARY_COMPONENT as FABRIC_INTERMEDIARY_COMPONENT

# Right now Quilt recommends using Fabric's intermediary
USE_QUILT_MAPPINGS = False

BASE_DIR = "quilt"

JARS_DIR = join(BASE_DIR, "jars")
INSTALLER_INFO_DIR = join(BASE_DIR, "loader-installer-json")
META_DIR = join(BASE_DIR, "meta-v3")

LOADER_COMPONENT = "org.quiltmc.quilt-loader"
INTERMEDIARY_COMPONENT = "org.quiltmc.hashed"

if not USE_QUILT_MAPPINGS:
    INTERMEDIARY_COMPONENT = FABRIC_INTERMEDIARY_COMPONENT

DISABLE_BEACON_ARG = "-Dloader.disable_beacon=true"
DISABLE_BEACON_VERSIONS = {
    "0.19.2-beta.3",
    "0.19.2-beta.4",
    "0.19.2-beta.5",
    "0.19.2-beta.6",
    "0.19.2-beta.7",
    "0.19.2",
    "0.19.3-beta.1",
    "0.19.3",
    "0.19.4",
    "0.20.0-beta.1",
    "0.20.0-beta.2",
    "0.20.0-beta.3",
    "0.20.0-beta.4",
    "0.20.0-beta.5",
    "0.20.0-beta.6",
    "0.20.0-beta.7",
    "0.20.0-beta.8",
    "0.20.0-beta.9",
    "0.20.0-beta.10",
    "0.20.0-beta.11",
    "0.20.0-beta.12",
    "0.20.0-beta.13",
    "0.20.0-beta.14",
}
