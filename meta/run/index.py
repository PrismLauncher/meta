import hashlib
import os
from operator import attrgetter

from meta.common import launcher_path, file_hash


from meta.model import MetaVersion, MetaPackage
from meta.model.index import (
    MetaPackageIndex,
    MetaVersionIndex,
    MetaVersionIndexEntry,
    MetaPackageIndexEntry,
)

LAUNCHER_DIR = launcher_path()


# ignore these files when indexing versions
ignore = {"index.json", "package.json", ".git", ".github"}

# initialize output structures - package list level
packages = MetaPackageIndex()

# walk through all the package folders
for package in sorted(os.listdir(LAUNCHER_DIR)):
    if package in ignore:
        continue

    sharedData = MetaPackage.parse_file(
        os.path.join(LAUNCHER_DIR, package, "package.json")
    )
    recommendedVersions = set()
    if sharedData.recommended:
        recommendedVersions = set(sharedData.recommended)

    # initialize output structures - version list level
    versionList = MetaVersionIndex(uid=package, name=sharedData.name)

    # walk through all the versions of the package
    for filename in os.listdir(LAUNCHER_DIR + "/%s" % package):
        if filename in ignore:
            continue
        # parse and hash the version file
        filepath = LAUNCHER_DIR + "/%s/%s" % (package, filename)
        filehash = file_hash(filepath, hashlib.sha256)
        versionFile = MetaVersion.parse_file(filepath)
        is_recommended = versionFile.version in recommendedVersions

        versionEntry = MetaVersionIndexEntry.from_meta_version(
            versionFile, is_recommended, filehash
        )

        versionList.versions.append(versionEntry)

    # sort the versions in descending order by time of release
    versionList.versions = sorted(
        versionList.versions, key=attrgetter("release_time"), reverse=True
    )

    # write the version index for the package
    outFilePath = LAUNCHER_DIR + "/%s/index.json" % package
    versionList.write(outFilePath)

    # insert entry into the package index
    packageEntry = MetaPackageIndexEntry(
        uid=package, name=sharedData.name, sha256=hash_file(hashlib.sha256, outFilePath)
    )
    packages.packages.append(packageEntry)

packages.write(os.path.join(LAUNCHER_DIR, "index.json"))
