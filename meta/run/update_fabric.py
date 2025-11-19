from collections import deque
from multiprocessing import Pool
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
from meta.common.fabric import (
    BROKEN_INTERMEDIARIES,
    JARS_DIR,
    INSTALLER_INFO_DIR,
    META_DIR,
    DATETIME_FORMAT_HTTP,
)
from meta.model.fabric import FabricJarInfo

UPSTREAM_DIR = upstream_path()

ensure_upstream_dir(JARS_DIR)
ensure_upstream_dir(INSTALLER_INFO_DIR)
ensure_upstream_dir(META_DIR)

sess = default_session()


def filehash(filename, hashtype, blocksize=65536):
    h = hashtype()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            h.update(block)
    return h.hexdigest()


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


def fetch_release_time(path, url):
    # These two approaches should result in the same metadata, except for the timestamp which might be a few minutes
    # off for the fallback method
    try:
        # Let's not download a Jar file if we don't need to.
        headers = head_file(url)
        tstamp = datetime.strptime(headers["Last-Modified"], DATETIME_FORMAT_HTTP)
    except requests.HTTPError:
        # Just in case something changes in the future
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

    return tstamp


def compute_jar_file_concurrent(it):
    print(f"Processing {it['maven']} ")
    path = os.path.join(UPSTREAM_DIR, JARS_DIR, transform_maven_key(it["maven"]))
    tstamp = BROKEN_INTERMEDIARIES.get(it["version"])
    if not tstamp:
        jar_maven_url = get_maven_url(
            it["maven"], "https://maven.fabricmc.net/", ".jar"
        )
        tstamp = fetch_release_time(
            path,
            jar_maven_url,
        )

    data = FabricJarInfo(release_time=tstamp)
    data.write(f"{path}.json")
    print(f"Processing {it['maven']} Done")


def get_json_file_concurrent(it):
    print(f"Downloading JAR info for loader {it['version']} ")
    maven_url = get_maven_url(it["maven"], "https://maven.fabricmc.net/", ".json")
    get_json_file(
        os.path.join(UPSTREAM_DIR, INSTALLER_INFO_DIR, f"{it['version']}.json"),
        maven_url,
    )
    print(f"Downloading JAR info for loader {it['version']} Done")


def main():
    # get the version list for each component we are interested in
    for component in ["intermediary", "loader"]:
        index = get_json_file(
            os.path.join(UPSTREAM_DIR, META_DIR, f"{component}.json"),
            "https://meta.fabricmc.net/v2/versions/" + component,
        )
        with Pool(None) as pool:
            deque(pool.imap_unordered(compute_jar_file_concurrent, index, 32), 0)

    # for each loader, download installer JSON file from maven
    with open(
        os.path.join(UPSTREAM_DIR, META_DIR, "loader.json"), "r", encoding="utf-8"
    ) as loaderVersionIndexFile:
        loader_version_index = json.load(loaderVersionIndexFile)
        with Pool(None) as pool:
            deque(
                pool.imap_unordered(get_json_file_concurrent, loader_version_index, 32),
                0,
            )


if __name__ == "__main__":
    main()
