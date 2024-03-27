import os
import datetime
from urllib.parse import urlparse
from typing import Any, Optional

import requests
from cachecontrol import CacheControl  # type: ignore
from cachecontrol.caches import FileCache  # type: ignore

LAUNCHER_MAVEN = "https://files.prismlauncher.org/maven/%s"


def serialize_datetime(dt: datetime.datetime):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc).isoformat()

    return dt.isoformat()


def launcher_path():
    if "LAUNCHER_DIR" in os.environ:
        return os.environ["LAUNCHER_DIR"]
    return "launcher"


def upstream_path():
    if "UPSTREAM_DIR" in os.environ:
        return os.environ["UPSTREAM_DIR"]
    return "upstream"


def static_path():
    if "STATIC_DIR" in os.environ:
        return os.environ["STATIC_DIR"]
    return "static"


def ensure_upstream_dir(path: str):
    path = os.path.join(upstream_path(), path)
    if not os.path.exists(path):
        os.makedirs(path)


def ensure_component_dir(component_id: str):
    path = os.path.join(launcher_path(), component_id)
    if not os.path.exists(path):
        os.makedirs(path)


def transform_maven_key(maven_key: str):
    return maven_key.replace(":", ".")


def replace_old_launchermeta_url(url: str):
    o = urlparse(url)
    if o.netloc == "launchermeta.mojang.com":
        return o._replace(netloc="piston-meta.mojang.com").geturl()

    return url


def get_all_bases(cls: type, bases: Optional[list[type]] = None):
    bases = bases or []
    bases.append(cls)
    for c in cls.__bases__:
        get_all_bases(c, bases)
    return tuple(bases)


def merge_dict(base: dict[Any, Any], overlay: dict[Any, Any]):
    for k, v in base.items():
        if isinstance(v, dict):
            merge_dict(v, overlay.setdefault(k, {}))  # type: ignore
        else:
            if k not in overlay:
                overlay[k] = v

    return overlay


def default_session():
    forever_cache = FileCache("caches/http_cache", forever=True)
    sess = CacheControl(requests.Session(), forever_cache)

    sess.headers.update({"User-Agent": "PrismLauncherMeta/1.0"})

    return sess
