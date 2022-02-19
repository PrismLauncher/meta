FROM python:3.10.2-bullseye

RUN pip install cachecontrol iso8601 requests lockfile jsonobject six \
    && apt-get update && apt-get install -y rsync cron

# add our cronjob
COPY docker/update.cron /etc/cron.d/meta-update
RUN chmod 644 /etc/cron.d/meta-update \
    && crontab /etc/cron.d/meta-update

# install entrypoint
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint

RUN useradd -Um user \
    && mkdir -p /home/user/.ssh \
    && ssh-keyscan github.com > /home/user/.ssh/known_hosts \
    && mkdir -p /app

COPY . /app/

ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["update"]
