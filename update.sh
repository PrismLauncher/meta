#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}" || exit 1
BASEDIR=$(pwd)

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
    launcher_git reset --hard HEAD
    exit 1
}

function upstream_git {
    git -C "${BASEDIR}/${UPSTREAM_DIR}" "$@"
}

function launcher_git {
    git -C "${BASEDIR}/${LAUNCHER_DIR}" "$@"
}

# make sure we *could* push to our repo

currentDate=$(date -I)

upstream_git reset --hard HEAD || exit 1
upstream_git checkout "${BRANCH}" || exit 1

python updateMojang.py || fail_in
python updateForge.py || fail_in
python updateNeoForge.py || fail_in
python updateFabric.py || fail_in
python updateQuilt.py || fail_in
python updateLiteloader.py || fail_in

if [ "${DEPLOY_TO_GIT}" = true ] ; then
    upstream_git add mojang/version_manifest_v2.json mojang/versions/* || fail_in
    upstream_git add forge/*.json forge/version_manifests/*.json forge/installer_manifests/*.json forge/files_manifests/*.json forge/installer_info/*.json || fail_in
    upstream_git add neoforge/*.json neoforge/version_manifests/*.json neoforge/installer_manifests/*.json neoforge/files_manifests/*.json neoforge/installer_info/*.json || fail_in
    upstream_git add fabric/loader-installer-json/*.json fabric/meta-v2/*.json fabric/jars/*.json || fail_in
    upstream_git add quilt/loader-installer-json/*.json quilt/meta-v3/*.json quilt/jars/*.json || fail_in
    upstream_git add liteloader/*.json || fail_in
    if ! upstream_git diff --cached --exit-code ; then
        upstream_git commit -a -m "Update ${currentDate}" || fail_in
        upstream_git push || exit 1
    fi
fi

launcher_git reset --hard HEAD || exit 1
launcher_git checkout "${BRANCH}" || exit 1

python generateMojang.py || fail_out
python generateForge.py || fail_out
python generateNeoForge.py || fail_out
python generateFabric.py || fail_out
python generateQuilt.py || fail_out
python generateLiteloader.py || fail_out
python index.py || fail_out

if [ "${DEPLOY_TO_GIT}" = true ] ; then
    launcher_git add index.json org.lwjgl/* org.lwjgl3/* net.minecraft/* || fail_out
    launcher_git add net.minecraftforge/* || fail_out
    launcher_git add net.neoforged/* || fail_out
    launcher_git add net.fabricmc.fabric-loader/* net.fabricmc.intermediary/* || fail_out
    launcher_git add org.quiltmc.quilt-loader/* || fail_out  # TODO: add Quilt hashed, once it is actually used
    launcher_git add com.mumfrey.liteloader/* || fail_out

    if ! launcher_git diff --cached --exit-code ; then
        launcher_git commit -a -m "Update ${currentDate}" || fail_out
        launcher_git push || exit 1
    fi
fi

if [ "${DEPLOY_TO_FOLDER}" = true ] ; then
    DEPLOY_FOLDER_var="DEPLOY_FOLDER_$MODE"
    DEPLOY_FOLDER="${!DEPLOY_FOLDER_var}"
    echo "Deploying to ${DEPLOY_FOLDER}"
    rsync -rvog --chown="${DEPLOY_FOLDER_USER}:${DEPLOY_FOLDER_GROUP}" --exclude=.git "${BASEDIR}/${LAUNCHER_DIR}/" "${DEPLOY_FOLDER}"
fi

exit 0
