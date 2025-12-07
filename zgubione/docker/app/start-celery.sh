#!/usr/bin/env bash

set -e

flag=0
retries=0
max_retries=2
sleep_time=3

opts=${CELERY_OPTS}
concurency=${CELERY_CONCURENCY:-2}
queues=${CELERY_QUEUES:-default,resources,indexing,indexing_data,periodic,newsletter,notifications,search_history,watchers,harvester,history,graphs,datasets,archiving,reports,discourse,showcases}
rabbitmq_host=${RABBITMQ_HOST:-mcod-rabbitmq:5672}

while [ $flag -eq 0 ]; do
    if [ $retries -eq $max_retries ]; then
        echo Executed $retries retries, aborting
        exit 1
    fi
    sleep $sleep_time
    wait-for-it $rabbitmq_host -s --timeout=30 -- celery --app=mcod.celeryapp:app worker -l INFO -Q $queues --concurrency=$concurency $opts
    if [ $? -eq 0 ]; then
        flag=1
    else
        echo "Cannot start celery, retrying in $sleep_time seconds..."
        let retries++
    fi
done
