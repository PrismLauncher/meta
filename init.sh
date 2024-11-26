#!/usr/bin/env bash

set -ex

if [ -f config.sh ]; then
    source config.sh
fi

export META_CACHE_DIR=${CACHE_DIRECTORY:-./caches}
export META_UPSTREAM_DIR=${META_UPSTREAM_DIR:-${STATE_DIRECTORY:-.}/upstream}
export META_LAUNCHER_DIR=${META_LAUNCHER_DIR:-${STATE_DIRECTORY:-.}/launcher}

function init_repo {
    # no op if target already exists
    if [ -d "$1" ]; then
        return 0
    fi

    # fail if no repo url is specified
    if [ -z "$2" ]; then
        echo "Can't initialize missing $1 directory. Please specify $3" >&2
        return 1
    fi

    git clone "$2" "$1"
}

init_repo "$META_UPSTREAM_DIR" "$META_UPSTREAM_URL" "META_UPSTREAM_URL"
init_repo "$META_LAUNCHER_DIR" "$META_LAUNCHER_URL" "META_LAUNCHER_URL"
