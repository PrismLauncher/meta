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
