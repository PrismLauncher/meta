#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}"
BASEDIR=`pwd`

set -x

export UPSTREAM_DIR=mojang
export MMC_DIR=multimc

function fail {
    git reset --hard HEAD
    exit 1
}

currentDate=`date --iso-8601`

./updateMojang.py || exit 1
cd "${BASEDIR}/${UPSTREAM_DIR}"
git add version_manifest.json versions/* assets/* || fail
if ! git diff --cached --exit-code ; then
    git commit -a -m "Update ${currentDate}" || fail
    git push || fail
fi
cd "${BASEDIR}"

./separateVersions.py || exit 1
cd "${BASEDIR}/${MMC_DIR}"
git add org.lwjgl/* net.minecraft/* || fail
if ! git diff --cached --exit-code ; then
    git commit -a -m "Update ${currentDate}" || fail
    git push || fail
fi
cd "${BASEDIR}"

exit 0
