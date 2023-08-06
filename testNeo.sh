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


python updateNeoForge.py || fail_in

launcher_git reset --hard HEAD || exit 1
launcher_git checkout "${BRANCH}" || exit 1


python generateNeoForge.py || fail_out
python index.py || fail_out