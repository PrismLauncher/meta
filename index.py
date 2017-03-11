#!/bin/python3

import hashlib
import os
import json

from metautil import *
from operator import itemgetter

# take the hash type (like hashlib.md5) and filename, return hex string of hash
def HashFile(hash, fname):
    hash_instance = hash()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_instance.update(chunk)
    return hash_instance.hexdigest()

# ignore these files when indexing versions
ignore = set(["index.json", ".git"])

# initialize output structures - package list level
packages = MultiMCPackageIndex()

# walk thorugh all the package folders
for package in os.listdir('multimc'):
    if package in ignore:
        continue

    # initialize output structures - version list level
    versionList = MultiMCVersionIndex()
    versionList.uid = package
    latest = {}
    name = None

    # walk through all the versions of the package
    for filename in os.listdir("multimc/%s" % (package)):
        if filename in ignore:
            continue

        # parse and hash the version file
        filepath = "multimc/%s/%s" % (package, filename)
        filehash = HashFile(hashlib.sha256, filepath)
        versionFile = None
        with open(filepath) as json_file:
            versionFile = MultiMCVersionFile(json.load(json_file))

        # pull information from the version file
        versionEntry = MultiMCVersionIndexEntry()
        versionEntry.version = versionFile.version
        versionEntry.type = versionFile.type
        versionEntry.releaseTime = versionFile.releaseTime
        versionEntry.sha256 = filehash
        if name == None:
            name = versionFile.name

        # update the latest version of particular type (if needed)
        if versionFile.type:
            if versionFile.type in latest:
                if latest[versionFile.type][1] < versionFile.releaseTime:
                    latest[versionFile.type] = (versionFile.version, versionFile.releaseTime)
            else:
                latest[versionFile.type] = (versionFile.version, versionFile.releaseTime)
        versionList.versions.append(versionEntry)

    # sort the versions in descending order by time of release
    versionList.versions = sorted(versionList.versions, key=itemgetter('releaseTime'), reverse=True)

    # assign some values derived from the version files
    versionList.name = name

    # if the latest version dict was populated, transform it into output
    if latest:
        versionList.latest = {}
        for type, (version, releaseTime) in latest.items():
            versionList.latest[type] = version

    # write the version index for the package
    outFilePath = "multimc/%s/index.json" % (package)
    with open(outFilePath, 'w') as outfile:
        json.dump(versionList.to_json(), outfile, sort_keys=True, indent=4)

    # insert entry into the package index
    packageEntry = MultiMCPackageIndexEntry(
            {
                "uid" : package,
                "name" : name,
                "sha256": HashFile(hashlib.sha256, outFilePath)
            }
        )
    packages.packages.append(packageEntry)

# write the repository package index
with open("multimc/index.json", 'w') as outfile:
    json.dump(packages.to_json(), outfile, sort_keys=True, indent=4)
