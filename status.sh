#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}" || exit 1
BASEDIR=$(pwd)

source config.sh

echo "Upstream:"
pushd "${UPSTREAM_DIR}" || exit 1
git status
popd || exit 1
echo


echo "PrismLauncher:"
pushd "${LAUNCHER_DIR}" || exit 1
git status
popd || exit 1
echo

echo "Scripts:"
git status
echo