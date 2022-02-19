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

BRANCH_var="BRANCH_$MODE"
BRANCH="${!BRANCH_var}"

function fail_in {
    upstream_git reset --hard HEAD
    exit 1
}

function fail_out {
    polymc_git reset --hard HEAD
    exit 1
}

function upstream_git {
    git -C "${BASEDIR}/${UPSTREAM_DIR}" $@
}

function polymc_git {
    git -C "${BASEDIR}/${UPSTREAM_DIR}" $@
}

currentDate=`date --iso-8601`

upstream_git reset --hard HEAD || exit 1
upstream_git checkout ${BRANCH} || exit 1

python updateMojang.py || fail_in
python updateForge.py || fail_in
python updateFabric.py || fail_in
python updateLiteloader.py || fail_in

if [ "${DEPLOY_TO_GIT}" = true ] ; then
    upstream_git add mojang/version_manifest_v2.json mojang/versions/* mojang/assets/* || fail_in
    upstream_git add forge/*.json forge/version_manifests/*.json forge/installer_manifests/*.json forge/files_manifests/*.json forge/installer_info/*.json || fail_in
    upstream_git add fabric/loader-installer-json/*.json fabric/meta-v2/*.json fabric/jars/*.json || fail_in
    upstream_git add liteloader/*.json || fail_in
    if ! upstream_git diff --cached --exit-code ; then
        upstream_git commit -a -m "Update ${currentDate}" || fail_in
        GIT_SSH_COMMAND="ssh -i ${BASEDIR}/config/deploy.key" upstream_git push || exit 1
    fi
fi

polymc_git reset --hard HEAD || exit 1
polymc_git checkout ${BRANCH} || exit 1

python generateMojang.py || fail_out
python generateForge.py || fail_out
python generateFabric.py || fail_in
python generateLiteloader.py || fail_out
python index.py || fail_out

if [ "${DEPLOY_TO_GIT}" = true ] ; then
    polymc_git add index.json org.lwjgl/* net.minecraft/* || fail_out
    polymc_git add net.minecraftforge/* || fail_out
    polymc_git add net.fabricmc.fabric-loader/* net.fabricmc.intermediary/* || fail_out
    polymc_git add com.mumfrey.liteloader/* || fail_out
    if [ -d "org.lwjgl3" ]; then
        polymc_git add org.lwjgl3/* || fail_out
    fi

    if ! polymc_git diff --cached --exit-code ; then
        polymc_git commit -a -m "Update ${currentDate}" || fail_out
        GIT_SSH_COMMAND="ssh -i ${BASEDIR}/config/deploy.key" polymc_git push || exit 1
    fi
fi

if [ "${UPDATE_FORGE_MAVEN}" = true ] ; then
    echo "Updating the copy of Forge maven"
    python enumerateForge.py
fi

if [ "${DEPLOY_TO_FOLDER}" = true ] ; then
    DEPLOY_FOLDER_var="DEPLOY_FOLDER_$MODE"
    DEPLOY_FOLDER="${!DEPLOY_FOLDER_var}"
    echo "Deploying to ${DEPLOY_FOLDER}"
    rsync -rvog --chown=${DEPLOY_FOLDER_USER}:${DEPLOY_FOLDER_GROUP} --exclude=.git ${BASEDIR}/${PMC_DIR}/ ${DEPLOY_FOLDER}
fi

exit 0
