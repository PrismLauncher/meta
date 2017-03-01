#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}"

function fail {
    git reset --hard HEAD
    exit 1
}

currentDate=`date --iso-8601`

./updateMojang.py || fail
git add mojang/version_manifest.json mojang/versions/* mojang/assets/* || fail

./separateVersions.py || fail
git add multimc/org.lwjgl/* multimc/net.minecraft/* || fail

git commit -a -m "Update ${currentDate}" || fail
git push || fail

exit 0
