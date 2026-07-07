#!/bin/bash
QBIT="http://localhost:8080"
LOG="/var/log/seed-finder.log"
touch "$LOG" 2>/dev/null; chmod 644 "$LOG" 2>/dev/null
log() { echo "$(date "+%H:%M:%S") $1" >> "$LOG"; }

curl -s -c /tmp/sf_cookie "$QBIT/api/v2/auth/login" --data-urlencode "username=admin" --data-urlencode "password=adminadmin" > /dev/null

STALLED=$(curl -s --max-time 10 -b /tmp/sf_cookie "$QBIT/api/v2/torrents/info?filter=stalled_downloading" | python3 -c "import json,sys;print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
[ "$STALLED" -eq 0 ] && exit 0
log "Stalled: $STALLED - re-announcing"

curl -s -b /tmp/sf_cookie -d "hashes=all" "$QBIT/api/v2/torrents/reannounce" > /dev/null
log "Done"
