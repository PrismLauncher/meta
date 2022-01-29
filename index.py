#!/usr/bin/python3
import hashlib
import json
import os
from operator import itemgetter

from metautil import *

PMC_DIR = os.environ["PMC_DIR"]

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
packages = PolyMCPackageIndex()

# walk thorugh all the package folders
for package in sorted(os.listdir(PMC_DIR)):
    if package in ignore:
        continue

    sharedData = readSharedPackageData(package)
    recommendedVersions = set()
    if sharedData.recommended:
        recommendedVersions = set(sharedData.recommended)

    # initialize output structures - version list level
    versionList = PolyMCVersionIndex()
    versionList.uid = package
    versionList.name = sharedData.name

    # walk through all the versions of the package
    for filename in os.listdir(PMC_DIR + "/%s" % (package)):
        if filename in ignore:
            continue

        # parse and hash the version file
        filepath = PMC_DIR + "/%s/%s" % (package, filename)
        filehash = HashFile(hashlib.sha256, filepath)
        versionFile = None
        with open(filepath) as json_file:
            versionFile = PolyMCVersionFile(json.load(json_file))

        # pull information from the version file
        versionEntry = PolyMCVersionIndexEntry()
        if versionFile.version in recommendedVersions:
            versionEntry.recommended = True
        versionEntry.version = versionFile.version
        versionEntry.type = versionFile.type
        versionEntry.releaseTime = versionFile.releaseTime
        versionEntry.sha256 = filehash
        versionEntry.requires = versionFile.requires
        versionEntry.conflicts = versionFile.conflicts
        versionEntry.volatile = versionFile.volatile
        versionList.versions.append(versionEntry)

    # sort the versions in descending order by time of release
    versionList.versions = sorted(versionList.versions, key=itemgetter('releaseTime'), reverse=True)

    # write the version index for the package
    outFilePath = PMC_DIR + "/%s/index.json" % (package)
    with open(outFilePath, 'w') as outfile:
        json.dump(versionList.to_json(), outfile, sort_keys=True, indent=4)

    # insert entry into the package index
    packageEntry = PolyMCPackageIndexEntry(
            {
                "uid" : package,
                "name" : sharedData.name,
                "sha256": HashFile(hashlib.sha256, outFilePath)
            }
        )
    packages.packages.append(packageEntry)

# write the repository package index
with open(PMC_DIR + "/index.json", 'w') as outfile:
    json.dump(packages.to_json(), outfile, sort_keys=True, indent=4)
