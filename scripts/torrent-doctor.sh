#!/bin/bash
set -euo pipefail
# torrent-doctor.sh — Self-healing torrent recovery
# Handles: stalled downloads, dead trackers, no peers, re-announce, force recheck, alt search
# Runs every 10 min via systemd timer

LOG="/mnt/20TB/homelab/media/Pipeline/logs/torrent-doctor.log"
QBIT="http://<local-ip>:8080"
COOKIE="/tmp/td_cookie"
RADARR_KEY="YOUR_RADARR_API_KEY"
SONARR_KEY="YOUR_SONARR_API_KEY"

log() { echo "$(date '+%H:%M:%S') $1" | tee -a "$LOG"; }

# Login
curl -s -c "$COOKIE" -L "$QBIT/api/v2/auth/login" \
    --data-urlencode 'username=topaz' \
    --data-urlencode 'password=YOUR_QBIT_PASSWORD' > /dev/null 2>&1

# --- 1. INJECT PUBLIC TRACKERS ---
log "Injecting public trackers..."
TRACKERS=(
    "udp://tracker.opentrackr.org:1337/announce"
    "udp://open.stealth.si:80/announce"
    "udp://tracker.torrent.eu.org:451/announce"
    "udp://explodie.org:6969/announce"
    "udp://tracker.coppersurfer.tk:6969/announce"
    "udp://9.rarbg.to:2710/announce"
    "udp://tracker.internetwarriors.net:1337/announce"
    "udp://ipv4.tracker.harry.lu:80/announce"
    "http://tracker.opentrackr.org:1337/announce"
    "udp://tracker.leechers-paradise.org:6969/announce"
    "udp://tracker.openbittorrent.com:6969/announce"
    "udp://open.demonii.com:1337/announce"
    "udp://tracker.moeking.me:6969/announce"
    "udp://tracker.bitsearch.to:1337/announce"
    "udp://tracker.tiny-vps.com:6969/announce"
    "udp://p4p.arenabg.com:1337/announce"
    "udp://movies.zsw.ca:6969/announce"
    "udp://retracker.lanta-net.ru:2710/announce"
    "udp://bt1.archive.org:6969/announce"
    "udp://bt2.archive.org:6969/announce"

    "udp://tracker.opentrackr.org:1337/announce"
    "udp://open.stealth.si:80/announce"
    "udp://tracker.torrent.eu.org:451/announce"
    "udp://explodie.org:6969/announce"
    "udp://tracker.coppersurfer.tk:6969/announce"
    "udp://9.rarbg.to:2710/announce"
    "udp://tracker.internetwarriors.net:1337/announce"
    "udp://ipv4.tracker.harry.lu:80/announce"
    "http://tracker.opentrackr.org:1337/announce"
)

# Get all torrents
torrents=$(curl -s -b "$COOKIE" "$QBIT/api/v2/torrents/info" 2>/dev/null)
total=$(echo "$torrents" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)

if [ "$total" -eq 0 ]; then
    log "  No torrents — skipping"
    rm -f "$COOKIE"
    exit 0
fi

# Get current trackers for all torrents
for t_hash in $(echo "$torrents" | python3 -c "import json,sys; [print(t['hash']) for t in json.load(sys.stdin)]" 2>/dev/null); do
    current=$(curl -s -b "$COOKIE" "$QBIT/api/v2/torrents/trackers?hash=$t_hash" 2>/dev/null)
    current_urls=$(echo "$current" | python3 -c "import json,sys; print(' '.join(t['url'] for t in json.load(sys.stdin)))" 2>/dev/null || echo "")
    
    missing=""
    for tr in "${TRACKERS[@]}"; do
        if ! echo "$current_urls" | grep -qF "$tr"; then
            missing="$missing$tr%0A"
        fi
    done
    
    if [ -n "$missing" ]; then
        missing=$(echo "$missing" | sed 's/%0A$//')
        curl -s -b "$COOKIE" -X POST "$QBIT/api/v2/torrents/addTrackers" \
            --data-urlencode "hash=$t_hash" \
            --data-urlencode "urls=$missing" > /dev/null 2>&1
    fi
done

# --- 2. RE-ANNOUNCE STALLED ---
log "Re-announcing stalled..."
stalled=$(curl -s -b "$COOKIE" "$QBIT/api/v2/torrents/info?filter=stalled_downloading" 2>/dev/null)
stalled_count=$(echo "$stalled" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)

if [ "$stalled_count" -gt 0 ]; then
    hashes=$(echo "$stalled" | python3 -c "import json,sys; print('|'.join(t['hash'] for t in json.load(sys.stdin)))" 2>/dev/null)
    curl -s -b "$COOKIE" -X POST "$QBIT/api/v2/torrents/reannounce" \
        --data-urlencode "hashes=$hashes" > /dev/null 2>&1
    log "  Re-announced $stalled_count stalled torrents"
fi

# --- 3. FORCE RECHECK LONG-STALLED (>2hr) ---
log "Force-rechecking long-stalled..."
long_stalled=$(echo "$stalled" | python3 -c "
import json,sys,time
now = time.time()
for t in json.load(sys.stdin):
    added = t.get('added_on', 0)
    if now - added > 7200:  # 2 hours
        print(t['hash'])
" 2>/dev/null)

if [ -n "$long_stalled" ]; then
    echo "$long_stalled" | while read -r h; do
        [ -n "$h" ] && curl -s -b "$COOKIE" -X POST "$QBIT/api/v2/torrents/recheck" \
            --data-urlencode "hashes=$h" > /dev/null 2>&1
    done
    long_count=$(echo "$long_stalled" | wc -l)
    log "  Force-rechecked $long_count long-stalled (>2hr)"
fi

# --- 4. FORCE RESUME ANY PAUSED/ERROR ---
log "Resuming paused/errored..."
for status in paused errored; do
    stuck=$(curl -s -b "$COOKIE" "$QBIT/api/v2/torrents/info?filter=$status" 2>/dev/null)
    stuck_hashes=$(echo "$stuck" | python3 -c "import json,sys; print('|'.join(t['hash'] for t in json.load(sys.stdin)))" 2>/dev/null)
    if [ -n "$stuck_hashes" ] && [ "$stuck_hashes" != "" ]; then
        curl -s -b "$COOKIE" -X POST "$QBIT/api/v2/torrents/resume" \
            --data-urlencode "hashes=$stuck_hashes" > /dev/null 2>&1
        stuck_count=$(echo "$stuck_hashes" | tr '|' '\n' | wc -l)
        log "  Resumed $stuck_count $status torrents"
    fi
done

# --- 5. DHT HEALTH CHECK ---
dht=$(curl -s -b "$COOKIE" "$QBIT/api/v2/transfer/info" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('dht_nodes',0))" 2>/dev/null || echo 0)
log "  DHT nodes: $dht"

# --- 6. SPEED REPORT ---
dl=$(curl -s -b "$COOKIE" "$QBIT/api/v2/transfer/info" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d.get('dl_info_speed',0)/1048576:.1f}\")" 2>/dev/null || echo 0)
active=$(curl -s -b "$COOKIE" "$QBIT/api/v2/torrents/info?filter=downloading" 2>/dev/null | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
total_t=$(curl -s -b "$COOKIE" "$QBIT/api/v2/torrents/info" 2>/dev/null | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
log "  Speed: ${dl}MB/s | Active: $active | Total: $total_t | Stalled: $stalled_count"

rm -f "$COOKIE"
log "Doctor complete"
