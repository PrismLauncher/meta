#!/usr/bin/env bash

set -x

if [ -f config.sh ]; then
    source config.sh
fi

export META_CACHE_DIR=${CACHE_DIRECTORY:-./caches}
export META_UPSTREAM_DIR=${META_UPSTREAM_DIR:-${STATE_DIRECTORY:-.}/upstream}
export META_LAUNCHER_DIR=${META_LAUNCHER_DIR:-${STATE_DIRECTORY:-.}/launcher}

function fail_in() {
    upstream_git reset --hard HEAD
    exit 1
}

function fail_out() {
    launcher_git reset --hard HEAD
    exit 1
}

function upstream_git() {
    git -C "${META_UPSTREAM_DIR}" "$@"
}

function launcher_git() {
    git -C "${META_LAUNCHER_DIR}" "$@"
}

# make sure we *could* push to our repo

currentDate=$(date -I)

upstream_git reset --hard HEAD || exit 1

python -m meta.run.update_mojang || fail_in
python -m meta.run.update_forge || fail_in
python -m meta.run.update_neoforge || fail_in
python -m meta.run.update_fabric || fail_in
python -m meta.run.update_quilt || fail_in
python -m meta.run.update_liteloader || fail_in
python -m meta.run.update_java || fail_in

if [ "${DEPLOY_TO_GIT}" = true ]; then
    upstream_git add mojang/version_manifest_v2.json mojang/java_all.json mojang/versions/* || fail_in
    upstream_git add forge/*.json forge/version_manifests/*.json forge/installer_manifests/*.json forge/files_manifests/*.json forge/installer_info/*.json || fail_in
    upstream_git add neoforge/*.json neoforge/version_manifests/*.json neoforge/installer_manifests/*.json neoforge/files_manifests/*.json neoforge/installer_info/*.json || fail_in
    upstream_git add fabric/loader-installer-json/*.json fabric/meta-v2/*.json fabric/jars/*.json || fail_in
    upstream_git add quilt/loader-installer-json/*.json quilt/meta-v3/*.json quilt/jars/*.json || fail_in
    upstream_git add liteloader/*.json || fail_in
    upstream_git add java_runtime/adoptium/available_releases.json java_runtime/adoptium/versions/*.json java_runtime/azul/packages.json java_runtime/azul/versions/*.json || fail_in
    if ! upstream_git diff --cached --exit-code; then
        upstream_git commit -a -m "Update ${currentDate}" || fail_in
        upstream_git push || exit 1
    fi
fi

launcher_git reset --hard HEAD || exit 1

python -m meta.run.generate_mojang || fail_out
python -m meta.run.generate_forge || fail_out
python -m meta.run.generate_neoforge || fail_out
python -m meta.run.generate_fabric || fail_out
python -m meta.run.generate_quilt || fail_out
python -m meta.run.generate_liteloader || fail_out
python -m meta.run.generate_java || fail_out
python -m meta.run.index || fail_out

if [ "${DEPLOY_TO_GIT}" = true ]; then
    launcher_git add index.json org.lwjgl/* org.lwjgl3/* net.minecraft/* || fail_out
    launcher_git add net.minecraftforge/* || fail_out
    launcher_git add net.neoforged/* || fail_out
    launcher_git add net.fabricmc.fabric-loader/* net.fabricmc.intermediary/* || fail_out
    launcher_git add org.quiltmc.quilt-loader/* || fail_out # TODO: add Quilt hashed, once it is actually used
    launcher_git add com.mumfrey.liteloader/* || fail_out
    launcher_git add net.minecraft.java/* net.adoptium.java/* com.azul.java/* || fail_out

    if ! launcher_git diff --cached --exit-code; then
        launcher_git commit -a -m "Update ${currentDate}" || fail_out
        launcher_git push || exit 1
    fi
fi

if [ "${DEPLOY_TO_FOLDER}" = true ]; then
    echo "Deploying to ${DEPLOY_FOLDER}"
    rsync -rvog --chown="${DEPLOY_FOLDER_USER}:${DEPLOY_FOLDER_GROUP}" --exclude=.git "${META_LAUNCHER_DIR}/" "${DEPLOY_FOLDER}"
fi

exit 0
