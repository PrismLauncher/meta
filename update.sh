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
cd "${BASEDIR}/${UPSTREAM_DIR}"
git add version_manifest.json versions/* assets/* || fail_in
if ! git diff --cached --exit-code ; then
    git commit -a -m "Update ${currentDate}" || fail_in
    git push || exit 1
fi
cd "${BASEDIR}"

./separateVersions.py || fail_out
./index.py || fail_out

cd "${BASEDIR}/${MMC_DIR}"
git add index.json org.lwjgl/* net.minecraft/* || fail_out
if ! git diff --cached --exit-code ; then
    git commit -a -m "Update ${currentDate}" || fail_out
    git push || exit 1
fi
cd "${BASEDIR}"

exit 0
