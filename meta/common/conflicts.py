from meta.model import Dependency
from .neoforge import NEOFORGE_COMPONENT
from .forge import FORGE_COMPONENT
from .fabric import LOADER_COMPONENT as FABRIC_LOADER_COMPONENT
from .quilt import LOADER_COMPONENT as QUILT_LOADER_COMPONENT
from .liteloader import LITELOADER_COMPONENT

LOADER_COMPONENTS = [
    NEOFORGE_COMPONENT, 
    FORGE_COMPONENT, 
    FABRIC_LOADER_COMPONENT,
    QUILT_LOADER_COMPONENT,
    LITELOADER_COMPONENT,
]

def loader_conflicts(exceptions: List[str]) -> List[Dependency]:
    return [Dependency(uid=uid) for uid in LOADER_COMPONENTS if (not uid in exceptions)]
