#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}"
BASEDIR=`pwd`

set -x

source config.sh

function fail_in {
    cd "${BASEDIR}/${UPSTREAM_DIR}"
    git reset --hard HEAD
    exit 1
}

function fail_out {
    cd "${BASEDIR}/${MMC_DIR}"
    git reset --hard HEAD
    exit 1
}

currentDate=`date --iso-8601`

./updateMojang.py || fail_in
./updateForge.py || fail_in
cd "${BASEDIR}/${UPSTREAM_DIR}"
git add mojang/version_manifest.json mojang/versions/* mojang/assets/* forge/*.json || fail_in
if ! git diff --cached --exit-code ; then
    git commit -a -m "Update ${currentDate}" || fail_in
    git push || exit 1
fi
cd "${BASEDIR}"

./generateMojang.py || fail_out
./generateForge.py || fail_out
./index.py || fail_out

cd "${BASEDIR}/${MMC_DIR}"
git add index.json org.lwjgl/* net.minecraft/* net.minecraftforge/* || fail_out
if ! git diff --cached --exit-code ; then
    git commit -a -m "Update ${currentDate}" || fail_out
    git push || exit 1
fi
cd "${BASEDIR}"

s3cmd --exclude=".git*" --delete-removed sync ${BASEDIR}/${MMC_DIR}/ s3://meta.multimc.org || exit 2

exit 0
