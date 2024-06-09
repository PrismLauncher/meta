import concurrent.futures
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
from meta.common.quilt import JARS_DIR, INSTALLER_INFO_DIR, META_DIR, USE_QUILT_MAPPINGS
from meta.common.fabric import DATETIME_FORMAT_HTTP
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
        print(f"QUILT DEBUG {r.headers}")
        version_json = r.json()
        json.dump(version_json, f, sort_keys=True, indent=4)
        return version_json


def head_file(url):
    r = sess.head(url)
    r.raise_for_status()
    return r.headers


def get_binary_file(path, url):
    with open(path, "wb") as f:
        r = sess.get(url)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=128):
            f.write(chunk)


def compute_jar_file(path, url):
    # NOTE: Quilt Meta does not make any guarantees about Last-Modified.
    # Always download the JAR file instead
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


def compute_jar_file_concurrent(component, it):
    print(f"Processing {component} {it['version']} ")
    jar_maven_url = get_maven_url(
        it["maven"], "https://maven.quiltmc.org/repository/release/", ".jar"
    )
    compute_jar_file(
        os.path.join(UPSTREAM_DIR, JARS_DIR, transform_maven_key(it["maven"])),
        jar_maven_url,
    )
    print(f"Processing {component} {it['version']} Done")


def get_json_file_concurrent(it):
    print(f"Downloading JAR info for loader {it['version']} ")
    maven_url = get_maven_url(
        it["maven"], "https://maven.quiltmc.org/repository/release/", ".json"
    )
    get_json_file(
        os.path.join(UPSTREAM_DIR, INSTALLER_INFO_DIR, f"{it['version']}.json"),
        maven_url,
    )


def main():
    # get the version list for each component we are interested in
    components = ["loader"]
    if USE_QUILT_MAPPINGS:
        components.append("hashed")
    for component in components:
        index = get_json_file(
            os.path.join(UPSTREAM_DIR, META_DIR, f"{component}.json"),
            "https://meta.quiltmc.org/v3/versions/" + component,
        )
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for it in index:
                executor.submit(compute_jar_file_concurrent, component, it)

        # for it in index:
        #     print(f"Processing {component} {it['version']} ")
        #     jar_maven_url = get_maven_url(
        #         it["maven"], "https://maven.quiltmc.org/repository/release/", ".jar"
        #     )
        #     compute_jar_file(
        #         os.path.join(UPSTREAM_DIR, JARS_DIR, transform_maven_key(it["maven"])),
        #         jar_maven_url,
        #     )

    # for each loader, download installer JSON file from maven
    with open(
        os.path.join(UPSTREAM_DIR, META_DIR, "loader.json"), "r", encoding="utf-8"
    ) as loaderVersionIndexFile:
        loader_version_index = json.load(loaderVersionIndexFile)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for it in loader_version_index:
                executor.submit(get_json_file_concurrent, it)
        # for it in loader_version_index:
        #     print(f"Downloading JAR info for loader {it['version']} ")
        #     maven_url = get_maven_url(
        #         it["maven"], "https://maven.quiltmc.org/repository/release/", ".json"
        #     )
        #     get_json_file(
        #         os.path.join(UPSTREAM_DIR, INSTALLER_INFO_DIR, f"{it['version']}.json"),
        #         maven_url,
        #     )


if __name__ == "__main__":
    main()
