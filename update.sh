#!/usr/bin/env bash

set -x

if [ -f config.sh ]; then
    source config.sh
fi

# Send Discord notification
function sendWebhook() {
    local message="$1"
    if [[ -z "$DISCORD_ID" ]] || [[-z "$DISCORD_TOKEN"]] || [[-z "$message"]]; then
        return
    fi

    local discordJsonData='{"username":"'"${DISCORD_USER}"'","content":"'"${message}"'"}'

    reponse=$(curl -s -H "Content-Type: application/json" -d "$discordJsonData" "https://discord.com/api/webhooks/"${DISCORD_ID}"/"${DISCORD_TOKEN})

    if [ $? -ne 0 ]; then
        echo "Error: Failed to send webhook message." >&2
        # echo "${response}" >&2
    fi
}

export META_CACHE_DIR=${CACHE_DIRECTORY:-./caches}
export META_UPSTREAM_DIR=${META_UPSTREAM_DIR:-${STATE_DIRECTORY:-.}/upstream}
export META_LAUNCHER_DIR=${META_LAUNCHER_DIR:-${STATE_DIRECTORY:-.}/launcher}

function fail_in() {
    sendWebhook "Meta failed to fetch: $1"
    upstream_git reset --hard HEAD
    exit 1
}

function fail_out() {
    sendWebhook "Meta failed to generate: $1"
    launcher_git reset --hard HEAD
    exit 1
}

function fail() {
    sendWebhook "Meta failed to: $1"
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

upstream_git reset --hard HEAD || fail "reset upstream"

python -m meta.run.update_mojang || fail_in "Mojang"
python -m meta.run.update_forge || fail_in "Forge"
python -m meta.run.update_neoforge || fail_in "Neoforge"
python -m meta.run.update_fabric || fail_in "Fabric"
python -m meta.run.update_quilt || fail_in "Quilt"
python -m meta.run.update_liteloader || fail_in "Liteloader"
python -m meta.run.update_java || fail_in "Java"

if [ "${DEPLOY_TO_GIT}" = true ]; then
    upstream_git add mojang/version_manifest_v2.json mojang/java_all.json mojang/versions/* || fail_in "add Mojang"
    upstream_git add forge/*.json forge/version_manifests/*.json forge/installer_manifests/*.json forge/files_manifests/*.json forge/installer_info/*.json || fail_in "add Forge"
    upstream_git add neoforge/*.json neoforge/version_manifests/*.json neoforge/installer_manifests/*.json neoforge/files_manifests/*.json neoforge/installer_info/*.json || fail_in "add Neoforge"
    upstream_git add fabric/loader-installer-json/*.json fabric/meta-v2/*.json fabric/jars/*.json || fail_in "add Fabric"
    upstream_git add quilt/loader-installer-json/*.json quilt/meta-v3/*.json quilt/jars/*.json || fail_in "add Quilt"
    upstream_git add liteloader/*.json || fail_in "add Liteloader"
    upstream_git add java_runtime/adoptium/available_releases.json java_runtime/adoptium/versions/*.json java_runtime/azul/packages.json java_runtime/azul/versions/*.json || fail_in "add Java"
    if ! upstream_git diff --cached --exit-code; then
        upstream_git commit -a -m "Update ${currentDate}" || fail_in "commit"
        upstream_git push || fail "push upstream"
    fi
fi

launcher_git reset --hard HEAD || fail "reset launcher"

python -m meta.run.generate_mojang || fail_out "Mojang"
python -m meta.run.generate_forge || fail_out "Forge"
python -m meta.run.generate_neoforge || fail_out "Neoforge"
python -m meta.run.generate_fabric || fail_out "Fabric"
python -m meta.run.generate_quilt || fail_out "Quilt"
python -m meta.run.generate_liteloader || fail_out "Liteloader"
python -m meta.run.generate_java || fail_out "Java"
python -m meta.run.index || fail_out "Index"

if [ "${DEPLOY_TO_GIT}" = true ]; then
    launcher_git add index.json org.lwjgl/* org.lwjgl3/* net.minecraft/* || fail_out "add Mojang"
    launcher_git add net.minecraftforge/* || fail_out "add Forge"
    launcher_git add net.neoforged/* || fail_out "add Neoforge"
    launcher_git add net.fabricmc.fabric-loader/* net.fabricmc.intermediary/* || fail_out "add Fabric"
    launcher_git add org.quiltmc.quilt-loader/* || fail_out "add Quilt" # TODO: add Quilt hashed, once it is actually used
    launcher_git add com.mumfrey.liteloader/* || fail_out "add Liteloader"
    launcher_git add net.minecraft.java/* net.adoptium.java/* com.azul.java/* || fail_out "add Java"

    if ! launcher_git diff --cached --exit-code; then
        launcher_git commit -a -m "Update ${currentDate}" || fail_out "commit"
        launcher_git push || fail "push launcher"
    fi
fi

if [ "${DEPLOY_TO_FOLDER}" = true ]; then
    echo "Deploying to ${DEPLOY_FOLDER}"
    rsync -rvog --chown="${DEPLOY_FOLDER_USER}:${DEPLOY_FOLDER_GROUP}" --exclude=.git "${LAUNCHER_DIR}/" "${DEPLOY_FOLDER}"
fi

exit 0
