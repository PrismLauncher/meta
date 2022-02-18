FROM python:3.10.2-bullseye

RUN pip install cachecontrol iso8601 requests lockfile jsonobject \
    && apt-get update && apt-get install -y rsync

RUN useradd -Ud /app user
USER user
WORKDIR /app

COPY . .

ENV MODE=master

CMD ["/bin/bash", "update.sh"]
