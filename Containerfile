FROM python:3.11.1-alpine3.17
ARG UID=1337
ARG GID=1337

RUN pip install pipenv \
    && apk add --no-cache rsync cronie git openssh bash

WORKDIR /app
COPY Pipfile Pipfile.lock .
RUN pipenv install --system --deploy

# add our cronjob
COPY docker/update.cron /etc/cron.d/meta-update
RUN chmod 644 /etc/cron.d/meta-update \
    && crontab /etc/cron.d/meta-update

# install entrypoint
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint

RUN addgroup -g $GID user \
    && adduser --disabled-password --ingroup user --uid $UID user \
    && mkdir -p /home/user/.ssh \
    && ssh-keyscan github.com > /home/user/.ssh/known_hosts \
    && mkdir -p /app \
    && chown -R $UID:$GID /app /home/user/.ssh

COPY . .

ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["update"]
