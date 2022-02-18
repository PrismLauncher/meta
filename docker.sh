#!/bin/bash
docker build metaenv -t metaenv

docker run -it --rm -e MODE=master -v $(pwd):/app metaenv:latest ./update.sh

