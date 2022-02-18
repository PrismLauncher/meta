FROM python:3.10.2-bullseye

RUN pip install cachecontrol iso8601 requests lockfile jsonobject

RUN apt update && apt install -y rsync

RUN useradd -Ud /app user

USER user

WORKDIR /app

