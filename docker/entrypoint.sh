#!/bin/bash
echo -n "Launch args: "
echo "$@"

if [ "$1" == "update" ]; then
    cd /app || exit 1
    exec su user -c "bash ./update.sh"
elif [ "$1" == "cron" ]; then
    exec crond -f
else
    exec "$@"
fi
