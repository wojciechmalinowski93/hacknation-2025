#!/usr/bin/env bash

set -e

flag=0
retries=0
max_retries=2
sleep_time=3

workers=${API_WORKERS:-2}
GUNICORN_CMD_ARGS=${GUNICORN_CMD_ARGS:-"--worker-class gevent --timeout=120"}

while [ $flag -eq 0 ]; do
    if [ $retries -eq $max_retries ]; then
        echo Executed $retries retries, aborting
        exit 1
    fi
    sleep $sleep_time
    if [ "$POSTGRES_HOST_TYPE" == "machine" ]; then
        python manage.py migrate
``        gunicorn mcod.api:app --workers=$workers --bind 0.0.0.0:8000 -R --env PYTHONUNBUFFERED=1 $GUNICORN_CMD_ARGS
    else
        wait-for-it mcod-db:5432 -s --timeout=10 -- python manage.py migrate
        wait-for-it mcod-db:5432 -s --timeout=10 -- gunicorn mcod.api:app --workers=$workers --bind 0.0.0.0:8000 -R --env PYTHONUNBUFFERED=1 $GUNICORN_CMD_ARGS
    fi
    if [ $? -eq 0 ]; then
        flag=1
    else
        echo "Cannot start api, retrying in $sleep_time seconds..."
        let retries++
    fi
done
