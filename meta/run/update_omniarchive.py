import concurrent.futures
import json
import os
import zipfile

from meta.common import upstream_path, ensure_upstream_dir, default_session
from meta.common.http import download_binary_file
from meta.common.omniarchive import (
    BASE_DIR,
    VERSION_MANIFEST_FILE,
    VERSIONS_DIR,
    ASSETS_DIR,
    JAVA_MANIFEST_FILE,
)
from meta.model.omniarchive import (
    OmniarchiveIndexWrap,
    OmniarchiveIndex,
    JavaIndex,
)

UPSTREAM_DIR = upstream_path()

ensure_upstream_dir(BASE_DIR)
ensure_upstream_dir(VERSIONS_DIR)
ensure_upstream_dir(ASSETS_DIR)

sess = default_session()

# i think this is for experiments but i'm keeping it for now bc i think we might need it for something else
def fetch_zipped_version(path, url):
    zip_path = f"{path}.zip"
    download_binary_file(sess, zip_path, url)
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.filename.endswith(".json"):
                print(f"Found {info.filename} as version json")
                version_json = json.load(z.open(info))
                break

    assert version_json

    with open(path, "w", encoding="utf-8") as f:
        json.dump(version_json, f, sort_keys=True, indent=4)

    return version_json


def fetch_version(path, url):
    r = sess.get(url)
    r.raise_for_status()
    version_json = r.json()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(version_json, f, sort_keys=True, indent=4)

    return version_json


MOJANG_JAVA_URL = "https://piston-meta.mojang.com/v1/products/java-runtime/2ec0cc96c44e5a76b9c8b7c39df7210883d12871/all.json"


def update_javas():
    r = sess.get(MOJANG_JAVA_URL)
    r.raise_for_status()

    remote_javas = JavaIndex(__root__=r.json())

    java_manifest_path = os.path.join(UPSTREAM_DIR, JAVA_MANIFEST_FILE)

    remote_javas.write(java_manifest_path)


def fetch_version_concurrent(remote_versions, x):
    version = remote_versions.versions[x]
    print(
        "Updating "
        + version.id
        + " to timestamp "
        + version.release_time.strftime("%s")
    )
    fetch_version(os.path.join(UPSTREAM_DIR, VERSIONS_DIR, f"{x}.json"), version.url)


def main():
    # get the remote version list
    r = sess.get("omnifest_json_url_here")
    r.raise_for_status()

    remote_versions = OmniarchiveIndexWrap(OmniarchiveIndex(**r.json()))
    remote_ids = set(remote_versions.versions.keys())

    version_manifest_path = os.path.join(UPSTREAM_DIR, VERSION_MANIFEST_FILE)

    if os.path.exists(version_manifest_path):
        # get the local version list
        current_versions = OmniarchiveIndexWrap(
            OmniarchiveIndex.parse_file(version_manifest_path)
        )
        local_ids = set(current_versions.versions.keys())

        # versions not present locally but present remotely are new
        pending_ids = remote_ids.difference(local_ids)

        for x in local_ids:
            remote_version = remote_versions.versions[x]
            local_version = current_versions.versions[x]
            if remote_version.time > local_version.time:
                pending_ids.add(x)
    else:
        pending_ids = remote_ids

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for x in pending_ids:
            executor.submit(fetch_version_concurrent, remote_versions, x)

    remote_versions.index.write(version_manifest_path)

    print("Getting Mojang Java runtime manfest")
    update_javas()


if __name__ == "__main__":
    main()
