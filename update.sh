#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}"
BASEDIR=`pwd`

set -x

source config.sh
if [ -f config/config_local.sh ]; then
    source config/config_local.sh
fi

MODE=${MODE:-develop}

S3_BUCKET_var="S3_$MODE"
S3_BUCKET="${!S3_BUCKET_var}"

BRANCH_var="BRANCH_$MODE"
BRANCH="${!BRANCH_var}"

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

cd "${BASEDIR}/${UPSTREAM_DIR}"
git reset --hard HEAD || exit 1
git checkout ${BRANCH} || exit 1
cd "${BASEDIR}"

./updateMojang.py || fail_in
./updateForge.py || fail_in
./updateLiteloader.py || fail_in

cd "${BASEDIR}/${UPSTREAM_DIR}"
git add mojang/version_manifest.json mojang/versions/* mojang/assets/* forge/*.json liteloader/*.json || fail_in
if ! git diff --cached --exit-code ; then
    git commit -a -m "Update ${currentDate}" || fail_in
    GIT_SSH_COMMAND="ssh -i ${BASEDIR}/config/meta-upstream.key" git push || exit 1
fi
cd "${BASEDIR}"

cd "${BASEDIR}/${MMC_DIR}"
git reset --hard HEAD || exit 1
git checkout ${BRANCH} || exit 1
cd "${BASEDIR}"

./generateMojang.py || fail_out
./generateForge.py || fail_out
./generateLiteloader.py || fail_out
./index.py || fail_out

cd "${BASEDIR}/${MMC_DIR}"
git add index.json org.lwjgl/* net.minecraft/* net.minecraftforge/* com.mumfrey.liteloader/* || fail_out
if ! git diff --cached --exit-code ; then
    git commit -a -m "Update ${currentDate}" || fail_out
    GIT_SSH_COMMAND="ssh -i ${BASEDIR}/config/meta-multimc.key" git push || exit 1
fi
cd "${BASEDIR}"

s3cmd -c ${BASEDIR}/config/s3cmd.cfg --exclude=".git*" --delete-removed sync ${BASEDIR}/${MMC_DIR}/ ${S3_BUCKET} || exit 2

exit 0
