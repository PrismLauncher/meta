#!/usr/bin/python3
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
import datetime
import hashlib

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def filehash(filename, hashtype, blocksize=65536):
    hash = hashtype()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()

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
legacyinfolist = ForgeLegacyInfoList()
tsPath = "static/forge-legacyinfo.json"

# get the installer jars - if needed - and get the installer profiles out of them
for id, entry in remoteVersionlist.number.items():
    if entry.mcversion == None:
        eprint ("Skipping %d with invalid MC version" % entry.build)
        continue

    version = ForgeVersion(entry, remoteVersionlist.artifact, remoteVersionlist.webpath)
    if version.url() == None:
        eprint ("Skipping %d with no valid files" % version.build)
        continue

    jarFilepath = "upstream/forge/%s" % version.filename()

    if version.usesInstaller():
        profileFilepath = "upstream/forge/%s.json" % version.longVersion
        if not os.path.isfile(profileFilepath):
            # grab the installer if it's not there
            if not os.path.isfile(jarFilepath):
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
    else:
        pass
        # ignore the two versions without install manifests and jar mod class files
        # TODO: fix those versions?
        if version.mcversion_sane == "1.6.1":
            continue

        # only gather legacy info if it's missing
        if not os.path.isfile(tsPath):
            # grab the jar/zip if it's not there
            if not os.path.isfile(jarFilepath):
                rfile = sess.get(version.url(), stream=True)
                rfile.raise_for_status()
                with open(jarFilepath, 'wb') as f:
                    for chunk in rfile.iter_content(chunk_size=128):
                        f.write(chunk)
            # find the latest timestamp in the zip file
            tstamp =  datetime.datetime.fromtimestamp(0)
            with zipfile.ZipFile(jarFilepath, 'r') as jar:
                allinfo = jar.infolist()
                for info in allinfo:
                    tstampNew = datetime.datetime(*info.date_time)
                    if tstampNew > tstamp:
                        tstamp = tstampNew
            legacyInfo = ForgeLegacyInfo()
            legacyInfo.releaseTime = tstamp
            legacyInfo.sha1 = filehash(jarFilepath, hashlib.sha1)
            legacyInfo.sha256 = filehash(jarFilepath, hashlib.sha256)
            legacyInfo.size = os.path.getsize(jarFilepath)
            legacyinfolist.number[id] = legacyInfo

# only write legacy info if it's missing
if not os.path.isfile(tsPath):
    with open(tsPath, 'w') as outfile:
        json.dump(legacyinfolist.to_json(), outfile, sort_keys=True, indent=4)
