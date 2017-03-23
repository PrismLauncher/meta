#!/usr/bin/python
'''
 Get the source files necessary for generating Forge versions
'''
from __future__ import print_function
import sys

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

import json
import zipfile
from forgeutil import *
from metautil import *
from jsonobject import *
import os.path

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

forever_cache = FileCache('http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)

# get the remote version list
r = sess.get('http://files.minecraftforge.net/maven/net/minecraftforge/forge/json')
r.raise_for_status()
main_json = r.json()
remoteVersionlist = ForgeIndex(main_json)
with open("upstream/forge/index.json", 'w', encoding='utf-8') as f:
    json.dump(main_json, f, sort_keys=True, indent=4)

versions = []

# get the installer jars - if needed - and get the installer profiles out of them
for id, entry in remoteVersionlist.number.items():
    if entry.mcversion == None:
        eprint ("Skipping %d with invalid MC version" % entry.build)
        continue

    version = ForgeVersion(entry, remoteVersionlist.artifact, remoteVersionlist.webpath)
    if version.url() == None:
        eprint ("Skipping %d with no valid files" % version.build)
        continue

    if version.usesInstaller():
        jarFilepath = "upstream/forge/%s" % version.filename()
        profileFilepath = "upstream/forge/%s.json" % version.longVersion
        if not os.path.isfile(profileFilepath):
            rfile = sess.get(version.url(), stream=True)
            rfile.raise_for_status()
            with open(jarFilepath, 'wb') as f:
                for chunk in rfile.iter_content(chunk_size=128):
                    f.write(chunk)
            with zipfile.ZipFile(jarFilepath, 'r') as jar:
                with jar.open('install_profile.json', 'r') as profileZipEntry:
                    with open(profileFilepath, 'wb') as profileFile:
                        profileFile.write(profileZipEntry.read())
                        profileFile.close()
                    profileZipEntry.close()
