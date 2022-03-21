import os


def polymc_path():
    if "PMC_DIR" in os.environ:
        return os.environ["PMC_DIR"]
    return "polymc"


def upstream_path():
    if "UPSTREAM_DIR" in os.environ:
        return os.environ["UPSTREAM_DIR"]
    return "upstream"


def ensure_component_dir(component_id):
    path = os.path.join(polymc_path(), component_id)
    if not os.path.exists(path):
        os.makedirs(path)
