#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}" || exit 1
BASEDIR=`pwd`

source config.sh

echo "Upstream:"
pushd "${UPSTREAM_DIR}"
git status
popd
echo


echo "PolyMC:"
pushd "${PMC_DIR}"
git status
popd
echo

echo "Scripts:"
git status
echo