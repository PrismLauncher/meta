#!/usr/bin/env bash

set -x

if [ -f config.sh ]; then
    source config.sh
fi

LOG_FILE=$(mktemp /tmp/meta-update.XXXXXX.log)
trap 'rm -f "$LOG_FILE"' EXIT
FAIL_HOOK=""

# Send Discord notification
function sendWebhook() {
    local message="$1"
    if [[ -z "$DISCORD_ID" ]] || [[ -z "$DISCORD_TOKEN" ]] || [[ -z "$message" ]]; then
        return
    fi

    local discordJsonData='{"username":"'"${DISCORD_USER}"'","content":"'"${message}"'"}'

    local response
    response=$(curl -s -F "payload_json=${discordJsonData}" \
        -F "files[0]=@${LOG_FILE};filename=update.log" \
        "https://discord.com/api/webhooks/${DISCORD_ID}/${DISCORD_TOKEN}")

    if [ $? -ne 0 ]; then
        echo "Error: Failed to send webhook message." >&2
        # echo "${response}" >&2
    fi
}

function run() {
    "$@" 2>&1 | tee "$LOG_FILE"
    local rc=${PIPESTATUS[0]}
    if [ "$rc" -ne 0 ]; then
        sendWebhook "Meta failed at $*"
        [ -n "$FAIL_HOOK" ] && $FAIL_HOOK
        exit 1
    fi
}

export META_CACHE_DIR=${CACHE_DIRECTORY:-./caches}
export META_UPSTREAM_DIR=${META_UPSTREAM_DIR:-${STATE_DIRECTORY:-.}/upstream}
export META_LAUNCHER_DIR=${META_LAUNCHER_DIR:-${STATE_DIRECTORY:-.}/launcher}

function upstream_git() {
    git -C "${META_UPSTREAM_DIR}" "$@"
}

function launcher_git() {
    git -C "${META_LAUNCHER_DIR}" "$@"
}

# make sure we *could* push to our repo

currentDate=$(date -I)

run upstream_git reset --hard HEAD
upstream_git pull

FAIL_HOOK="upstream_git reset --hard HEAD"
run python -m meta.run.update_mojang
run python -m meta.run.update_forge
run python -m meta.run.update_neoforge
run python -m meta.run.update_fabric
run python -m meta.run.update_quilt
run python -m meta.run.update_liteloader
run python -m meta.run.update_java

if [ "${DEPLOY_TO_GIT}" = true ]; then
    run upstream_git add mojang/version_manifest_v2.json mojang/java_all.json mojang/versions/*
    run upstream_git add forge/*.json forge/version_manifests/*.json forge/installer_manifests/*.json forge/files_manifests/*.json forge/installer_info/*.json forge/jars/*.sha1
    run upstream_git add neoforge/*.json neoforge/version_manifests/*.json neoforge/installer_manifests/*.json neoforge/files_manifests/*.json neoforge/installer_info/*.json neoforge/jars/*.sha1
    run upstream_git add fabric/loader-installer-json/*.json fabric/meta-v2/*.json fabric/jars/*.json
    run upstream_git add quilt/loader-installer-json/*.json quilt/meta-v3/*.json quilt/jars/*.json
    run upstream_git add liteloader/*.json
    run upstream_git add java_runtime/adoptium/available_releases.json java_runtime/adoptium/versions/*.json java_runtime/azul/packages.json java_runtime/azul/versions/*.json java_runtime/ibm/available_releases.json java_runtime/ibm/versions/*.json
    if ! upstream_git diff --cached --exit-code; then
        run upstream_git commit -a -m "Update ${currentDate}"
        run upstream_git push
    fi
fi

FAIL_HOOK=""
run launcher_git reset --hard HEAD
launcher_git pull

FAIL_HOOK="launcher_git reset --hard HEAD"
run python -m meta.run.generate_mojang
run python -m meta.run.generate_forge
run python -m meta.run.generate_neoforge
run python -m meta.run.generate_fabric
run python -m meta.run.generate_quilt
run python -m meta.run.generate_liteloader
run python -m meta.run.generate_java
run python -m meta.run.index

if [ "${DEPLOY_TO_GIT}" = true ]; then
    run launcher_git add index.json org.lwjgl/* org.lwjgl3/* net.minecraft/*
    run launcher_git add net.minecraftforge/*
    run launcher_git add net.neoforged/*
    run launcher_git add net.fabricmc.fabric-loader/* net.fabricmc.intermediary/*
    run launcher_git add org.quiltmc.quilt-loader/* # TODO: add Quilt hashed, once it is actually used # TODO: add Quilt hashed, once it is actually used
    run launcher_git add com.mumfrey.liteloader/*
    run launcher_git add net.minecraft.java/* net.adoptium.java/* com.azul.java/* com.ibm.java/*

    if ! launcher_git diff --cached --exit-code; then
        run launcher_git commit -a -m "Update ${currentDate}"
        run launcher_git push
    fi
fi

if [ "${DEPLOY_TO_FOLDER}" = true ]; then
    echo "Deploying to ${DEPLOY_FOLDER}"
    rsync -rvog --chown="${DEPLOY_FOLDER_USER}:${DEPLOY_FOLDER_GROUP}" --exclude=.git "${META_LAUNCHER_DIR}/" "${DEPLOY_FOLDER}"
fi

exit 0
