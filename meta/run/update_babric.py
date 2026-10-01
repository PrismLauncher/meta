import json
import os
import zipfile
from datetime import datetime

import requests

from meta.common import (
    upstream_path,
    ensure_upstream_dir,
    transform_maven_key,
    default_session,
)
from meta.common.babric import (
    GLASS_MAVEN,
    BABRIC_META,
    JARS_DIR,
    META_DIR,
    DATETIME_FORMAT_HTTP,
)
from meta.model.fabric import FabricJarInfo

UPSTREAM_DIR = upstream_path()

ensure_upstream_dir(JARS_DIR)
ensure_upstream_dir(META_DIR)

sess = default_session()


def get_maven_url(maven_key, server, ext):
    parts = maven_key.split(":", 3)
    maven_ver_url = (
        server + parts[0].replace(".", "/") + "/" + parts[1] + "/" + parts[2] + "/"
    )
    maven_url = maven_ver_url + parts[1] + "-" + parts[2] + ext
    return maven_url


def get_json_file(path, url):
    with open(path, "w", encoding="utf-8") as f:
        r = sess.get(url)
        r.raise_for_status()
        version_json = r.json()
        json.dump(version_json, f, sort_keys=True, indent=4)
        return version_json


def head_file(url):
    r = sess.head(url)
    r.raise_for_status()
    return r.headers


def get_binary_file(path, url):
    r = sess.get(url)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=128):
            f.write(chunk)


def compute_jar_file(path, url):
    try:
        headers = head_file(url)
        tstamp = datetime.strptime(headers["Last-Modified"], DATETIME_FORMAT_HTTP)
    except (requests.HTTPError, KeyError):
        print(f"Falling back to downloading jar for {url}")
        jar_path = path + ".jar"
        get_binary_file(jar_path, url)
        tstamp = datetime.fromtimestamp(0)
        with zipfile.ZipFile(jar_path) as jar:
            allinfo = jar.infolist()
            for info in allinfo:
                tstamp_new = datetime(*info.date_time)
                if tstamp_new > tstamp:
                    tstamp = tstamp_new

    data = FabricJarInfo(release_time=tstamp)
    data.write(path + ".json")


def main():
    for component in ["intermediary", "loader"]:
        get_json_file(
            os.path.join(UPSTREAM_DIR, META_DIR, f"{component}.json"),
            f"{BABRIC_META}v2/versions/{component}",
        )

    with open(
        os.path.join(UPSTREAM_DIR, META_DIR, "intermediary.json"), "r", encoding="utf-8"
    ) as f:
        intermediary_index = json.load(f)

    for entry in intermediary_index:
        print(f"Processing intermediary {entry['version']}")
        jar_url = get_maven_url(entry["maven"], GLASS_MAVEN, ".jar")
        compute_jar_file(
            os.path.join(UPSTREAM_DIR, JARS_DIR, transform_maven_key(entry["maven"])),
            jar_url,
        )


if __name__ == "__main__":
    main()
