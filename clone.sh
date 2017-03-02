#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}"
BASEDIR=`pwd`

source config.sh

set -x

if [ ! -d "${UPSTREAM_DIR}" ]; then
    git clone ${UPSTREAM_REPO} ${UPSTREAM_DIR}
fi

if [ ! -d "${MMC_DIR}" ]; then
    git clone ${MMC_REPO} ${MMC_DIR}
fi
