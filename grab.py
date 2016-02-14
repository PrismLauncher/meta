#!/usr/bin/python
import requests
from cachecontrol import CacheControl
import json
import pprint
import os
import argparse
import sys
from time import gmtime, strftime
from subprocess import Popen, PIPE

from cachecontrol.caches import FileCache

forever_cache = FileCache('http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)

parser = argparse.ArgumentParser(description='Download Mojang version files.')
args = parser.parse_args()

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
    
def grab_versions(main_json):
  assets = {}
  for version in main_json['versions']:
    url = version["url"]
    version_id = version["id"]
    print("version", version_id, url)
    assetId, assetUrl = get_version_file( "versions/" + version_id + '.json', url)
    assets[assetId] = assetUrl

  for assetId, assetUrl in iter(assets.items()):
    print("assets", assetId, assetUrl)
    get_file( "assets/" + assetId + '.json', assetUrl)

Popen(["rm *.json"], shell=True, stdout=PIPE).communicate()
Popen(["rm versions/*.json"], shell=True, stdout=PIPE).communicate()

r = sess.get('https://launchermeta.mojang.com/mc/game/version_manifest.json')
r.raise_for_status()
main_json = r.json()

with open("version_manifest.json", 'w', encoding='utf-8') as f:
  json.dump(main_json, f, sort_keys=True, indent=4)

grab_versions(main_json)

Popen(["git add version_manifest.json versions/* assets/*"], shell=True, stdout=PIPE).communicate()

Popen(["git commit -a -m \"Update " + strftime("%Y-%m-%d", gmtime()) + "\""], shell=True, stdout=PIPE).communicate()
Popen(["git push"], shell=True, stdout=PIPE).communicate()
