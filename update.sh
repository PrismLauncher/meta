#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}"
BASEDIR=`pwd`

#set -x

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
./updateForge2.py || fail_in
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
./generateForge2.py || fail_out
./generateLiteloader.py || fail_out
./index.py || fail_out

cd "${BASEDIR}/${MMC_DIR}"
git add index.json org.lwjgl/* net.minecraft/* net.minecraftforge/* com.mumfrey.liteloader/* || fail_out
if [ -d "org.lwjgl3" ]; then
    git add org.lwjgl3/* || fail_out
fi

if ! git diff --cached --exit-code ; then
    git commit -a -m "Update ${currentDate}" || fail_out
    GIT_SSH_COMMAND="ssh -i ${BASEDIR}/config/meta-multimc.key" git push || exit 1
fi
cd "${BASEDIR}"

if [ "${DEPLOY_TO_FOLDER}" = true ] ; then
    DEPLOY_FOLDER_var="DEPLOY_FOLDER_$MODE"
    DEPLOY_FOLDER="${!DEPLOY_FOLDER_var}"
    echo "Deploying to ${DEPLOY_FOLDER}"
    rsync -rvog --chown=${DEPLOY_FOLDER_USER}:${DEPLOY_FOLDER_GROUP} --exclude=.git /root/meta/multimc/ ${DEPLOY_FOLDER}
fi
if [ "${DEPLOY_TO_S3}" = true ] ; then
    s3cmd -c ${BASEDIR}/config/s3cmd.cfg --exclude=".git*" --delete-removed sync ${BASEDIR}/${MMC_DIR}/ ${S3_BUCKET} || exit 2
fi

exit 0
