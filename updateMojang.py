#!/usr/bin/python3
import json
import os

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
from metautil import *

UPSTREAM_DIR = os.environ["UPSTREAM_DIR"]

forever_cache = FileCache('http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)

def get_version_file(path, url):
    with open(path, 'w', encoding='utf-8') as f:
        r = sess.get(url)
        r.raise_for_status()
        version_json = r.json()
        assetId = version_json["assetIndex"]["id"]
        assetUrl = version_json["assetIndex"]["url"]
        json.dump(version_json, f, sort_keys=True, indent=4)
        return assetId, assetUrl

def get_file(path, url):
    with open(path, 'w', encoding='utf-8') as f:
        r = sess.get(url)
        r.raise_for_status()
        version_json = r.json()
        json.dump(version_json, f, sort_keys=True, indent=4)

# get the local version list
localVersionlist = None
try:
    with open(UPSTREAM_DIR + "/mojang/version_manifest_v2.json", 'r', encoding='utf-8') as localIndexFile:
        localVersionlist = MojangIndexWrap(json.load(localIndexFile))
except:
    localVersionlist = MojangIndexWrap({})
localIDs = set(localVersionlist.versions.keys())

# get the remote version list
r = sess.get('https://launchermeta.mojang.com/mc/game/version_manifest_v2.json')
r.raise_for_status()
main_json = r.json()
remoteVersionlist = MojangIndexWrap(main_json)
remoteIDs = set(remoteVersionlist.versions.keys())

# versions not present locally but present remotely are new
newIDs = remoteIDs.difference(localIDs)

# versions present both locally and remotely need to be checked
checkedIDs = remoteIDs.difference(newIDs)

# versions that actually need to be updated have updated timestamps or are new
updatedIDs = newIDs
for id in checkedIDs:
    remoteVersion = remoteVersionlist.versions[id]
    localVersion = localVersionlist.versions[id]
    if remoteVersion.time > localVersion.time:
        updatedIDs.add(id)

# update versions and the linked assets files
assets = {}
for id in updatedIDs:
    version = remoteVersionlist.versions[id]
    print("Updating " + version.id + " to timestamp " + version.releaseTime.strftime('%s'))
    assetId, assetUrl = get_version_file( UPSTREAM_DIR + "/mojang/versions/" + id + '.json', version.url)
    assets[assetId] = assetUrl

for assetId, assetUrl in iter(assets.items()):
    print("assets", assetId, assetUrl)
    get_file( UPSTREAM_DIR + "/mojang/assets/" + assetId + '.json', assetUrl)

with open(UPSTREAM_DIR + "/mojang/version_manifest_v2.json", 'w', encoding='utf-8') as f:
    json.dump(main_json, f, sort_keys=True, indent=4)
