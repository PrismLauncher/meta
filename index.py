#!/usr/bin/python3

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
ignore = set(["index.json", "package.json", ".git"])

# initialize output structures - package list level
packages = MultiMCPackageIndex()

# walk thorugh all the package folders
for package in os.listdir('multimc'):
    if package in ignore:
        continue

    sharedData = readSharedPackageData(package)
    recommendedVersions = set()
    if sharedData.recommended:
        recommendedVersions = set(sharedData.recommended)

    # initialize output structures - version list level
    versionList = MultiMCVersionIndex()
    versionList.uid = package
    versionList.parentUid = sharedData.parentUid
    versionList.name = sharedData.name

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
        if versionFile.version in recommendedVersions:
            versionEntry.recommended = True
        versionEntry.version = versionFile.version
        versionEntry.type = versionFile.type
        versionEntry.releaseTime = versionFile.releaseTime
        versionEntry.sha256 = filehash
        versionEntry.requires = versionFile.requires
        versionEntry.conflicts = versionFile.conflicts
        versionList.versions.append(versionEntry)

    # sort the versions in descending order by time of release
    versionList.versions = sorted(versionList.versions, key=itemgetter('releaseTime'), reverse=True)

    # write the version index for the package
    outFilePath = "multimc/%s/index.json" % (package)
    with open(outFilePath, 'w') as outfile:
        json.dump(versionList.to_json(), outfile, sort_keys=True, indent=4)

    # insert entry into the package index
    packageEntry = MultiMCPackageIndexEntry(
            {
                "uid" : package,
                "name" : sharedData.name,
                "sha256": HashFile(hashlib.sha256, outFilePath)
            }
        )
    packageEntry.parentUid = sharedData.parentUid
    packages.packages.append(packageEntry)

# write the repository package index
with open("multimc/index.json", 'w') as outfile:
    json.dump(packages.to_json(), outfile, sort_keys=True, indent=4)
