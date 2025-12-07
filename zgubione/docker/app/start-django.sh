#!/usr/bin/env bash

set -e

flag=0
retries=0
max_retries=2
sleep_time=3
debug=${DEBUG:-"no"}
concurency=${WEB_CONCURRENCY:-5}
component=${COMPONENT:-admin}

server_params="--bind 0.0.0.0:8001"

if [ "$COMPONENT"  == "ws" ]; then
    if [ "$DEBUG" == "yes" ]; then
        server_params="$server_params --debug --reload --workers 1"
    else
        server_params="$server_params --workers $concurency"
    fi
    server_cmd="hypercorn $server_params mcod.asgi:application"
else
    if [ "$DEBUG" == "yes" ]; then
        server_params="$server_params --timeout 3600 --reload --workers 1"
    else
        server_params="$server_params --timeout 3600 --workers $concurency --env PYTHONUNBUFFERED=1"
    fi
    server_cmd="gunicorn mcod.wsgi $server_params"

fi

while [ $flag -eq 0 ]; do
    if [ $retries -eq $max_retries ]; then
        echo Executed $retries retries, aborting
        exit 1
    fi
    sleep $sleep_time

    if [ "$POSTGRES_HOST_TYPE" == "machine" ]; then
        $server_cmd
    else
        wait-for-it mcod-db:5432 -s --timeout=30 -- $server_cmd
    fi

    if [ $? -eq 0 ]; then
        flag=1
    else
        echo "Cannot start admin panel, retrying in $sleep_time seconds..."
        let retries++
    fi
done
