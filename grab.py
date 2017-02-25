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

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

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
    assetId, assetUrl = get_version_file( "mojang/versions/" + version_id + '.json', url)
    assets[assetId] = assetUrl

  for assetId, assetUrl in iter(assets.items()):
    print("assets", assetId, assetUrl)
    get_file( "mojang/assets/" + assetId + '.json', assetUrl)

Popen(["rm mojang/*.json"], shell=True, stdout=PIPE).communicate()
Popen(["rm mojang/versions/*.json"], shell=True, stdout=PIPE).communicate()

r = sess.get('https://launchermeta.mojang.com/mc/game/version_manifest.json')
r.raise_for_status()
main_json = r.json()

with open("mojang/version_manifest.json", 'w', encoding='utf-8') as f:
  json.dump(main_json, f, sort_keys=True, indent=4)

grab_versions(main_json)

Popen(["git add mojang/version_manifest.json mojang/versions/* mojang/assets/*"], shell=True, stdout=PIPE).communicate()

print("Generating new split versions.")

Popen(["rm multimc/org.lwjgl/*.json"], shell=True, stdout=PIPE).communicate()
Popen(["rm multimc/net.minecraft/*.json"], shell=True, stdout=PIPE).communicate()

Popen(["./separateVersions.py"], shell=True, stdout=PIPE).communicate()

Popen(["git add multimc/org.lwjgl/* multimc/net.minecraft/*"], shell=True, stdout=PIPE).communicate()

#Popen(["git commit -a -m \"Update " + strftime("%Y-%m-%d", gmtime()) + "\""], shell=True, stdout=PIPE).communicate()
#Popen(["git push"], shell=True, stdout=PIPE).communicate()
