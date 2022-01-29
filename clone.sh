#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}"
BASEDIR=`pwd`

source config.sh

set -x

if [ ! -d "${UPSTREAM_DIR}" ]; then
    git clone ${UPSTREAM_REPO} ${UPSTREAM_DIR}
fi

if [ ! -d "${PMC_DIR}" ]; then
    git clone ${PMC_REPO} ${PMC_DIR}
fi
