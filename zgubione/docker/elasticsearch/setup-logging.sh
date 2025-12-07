#!/usr/bin/env bash

curl -XPUT -H 'Content-Type: application/json' 'http://localhost:9200/_all/_settings?preserve_existing=true' -d '{
   "index.indexing.slowlog.level" : "info",
   "index.indexing.slowlog.source" : "1000",
   "index.indexing.slowlog.threshold.index.debug" : "1s",
   "index.indexing.slowlog.threshold.index.info" : "3s",
   "index.indexing.slowlog.threshold.index.trace" : "500ms",
   "index.indexing.slowlog.threshold.index.warn" : "5s",
   "index.search.slowlog.level" : "info",
   "index.search.slowlog.threshold.fetch.debug" : "500ms",
   "index.search.slowlog.threshold.fetch.info" : "800ms",
   "index.search.slowlog.threshold.fetch.trace" : "200ms",
   "index.search.slowlog.threshold.fetch.warn" : "1s",
   "index.search.slowlog.threshold.query.debug" : "1s",
   "index.search.slowlog.threshold.query.info" : "3s",
   "index.search.slowlog.threshold.query.trace" : "500ms",
   "index.search.slowlog.threshold.query.warn" : "5s"
}'
