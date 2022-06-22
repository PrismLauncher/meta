import os
import datetime
from urllib.parse import urlparse


def serialize_datetime(dt: datetime.datetime):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc).isoformat()

    return dt.isoformat()


def polymc_path():
    if "PMC_DIR" in os.environ:
        return os.environ["PMC_DIR"]
    return "polymc"


def upstream_path():
    if "UPSTREAM_DIR" in os.environ:
        return os.environ["UPSTREAM_DIR"]
    return "upstream"


def static_path():
    if "STATIC_DIR" in os.environ:
        return os.environ["STATIC_DIR"]
    return "static"


def ensure_upstream_dir(path):
    path = os.path.join(upstream_path(), path)
    if not os.path.exists(path):
        os.makedirs(path)


def ensure_component_dir(component_id):
    path = os.path.join(polymc_path(), component_id)
    if not os.path.exists(path):
        os.makedirs(path)


def transform_maven_key(maven_key: str):
    return maven_key.replace(":", ".")

def replace_old_launchermeta_url(url):
    o = urlparse(url)
    if o.netloc == "launchermeta.mojang.com":
        return o._replace(netloc="piston-meta.mojang.com").geturl()

    return url
