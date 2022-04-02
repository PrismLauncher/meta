import json
import os.path

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

from meta.common import upstream_path, ensure_upstream_dir
from meta.common.mojang import BASE_DIR, VERSION_MANIFEST_FILE, VERSIONS_DIR, ASSETS_DIR
from meta.model.mojang import MojangIndexWrap, MojangIndex

UPSTREAM_DIR = upstream_path()

ensure_upstream_dir(BASE_DIR)
ensure_upstream_dir(VERSIONS_DIR)
ensure_upstream_dir(ASSETS_DIR)

forever_cache = FileCache('caches/http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)


def fetch_version_file(path, url):
    version_json = fetch_file(path, url)
    asset_id = version_json["assetIndex"]["id"]
    asset_url = version_json["assetIndex"]["url"]
    return asset_id, asset_url


def fetch_file(path, url):
    r = sess.get(url)
    r.raise_for_status()
    version_json = r.json()

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(version_json, f, sort_keys=True, indent=4)

    return version_json


def main():
    # get the remote version list
    r = sess.get('https://launchermeta.mojang.com/mc/game/version_manifest_v2.json')
    r.raise_for_status()

    remote_versions = MojangIndexWrap(MojangIndex(**r.json()))
    remote_ids = set(remote_versions.versions.keys())

    version_manifest = os.path.join(UPSTREAM_DIR, VERSION_MANIFEST_FILE)

    if os.path.exists(version_manifest):
        # get the local version list
        current_versions = MojangIndexWrap(MojangIndex.parse_file(version_manifest))
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

    # update versions and the linked assets files
    assets = {}
    for x in pending_ids:
        version = remote_versions.versions[x]
        print("Updating " + version.id + " to timestamp " + version.releaseTime.strftime('%s'))
        asset_id, asset_url = fetch_version_file(os.path.join(UPSTREAM_DIR, VERSIONS_DIR, f"{x}.json"), version.url)
        assets[asset_id] = asset_url

    for asset_id, asset_url in assets.items():
        print("assets", asset_id, asset_url)
        fetch_file(os.path.join(UPSTREAM_DIR, ASSETS_DIR, f"{asset_id}.json"), asset_url)

    remote_versions.index.write(version_manifest)


if __name__ == '__main__':
    main()
