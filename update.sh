#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}"

export UPSTREAM_DIR=mojang
export MMC_DIR=multimc

function fail {
    git reset --hard HEAD
    exit 1
}

currentDate=`date --iso-8601`

./updateMojang.py || fail
cd "${BASEDIR}/${UPSTREAM_DIR}"
git add version_manifest.json versions/* assets/* || fail
git commit -a -m "Update ${currentDate}" || fail
git push || fail
cd "${BASEDIR}"

./separateVersions.py || fail
cd "${BASEDIR}/${MMC_DIR}"
git add org.lwjgl/* net.minecraft/* || fail
git commit -a -m "Update ${currentDate}" || fail
git push || fail
cd "${BASEDIR}"

exit 0
