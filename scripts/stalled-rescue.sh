#!/bin/bash
# stalled-rescue.sh — Force resume stuck torrents at 95%+
LOG="/mnt/20TB/homelab/media/Pipeline/logs/stalled-rescue.log"
log() { echo "$(date '+%H:%M:%S') $1" | tee -a "$LOG"; }
log '=== Stalled rescue scan ==='
python3 -c "
import urllib.request, urllib.parse, json
rescued = 0
for label, url in [('OVERFLOW', 'http://127.0.0.1:8083'), ('LAPTOP', 'http://<local-ip>:8080')]:
    try:
        cj = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(cj)
        o.open(urllib.request.Request(f'{url}/api/v2/auth/login', data=urllib.parse.urlencode({'username':'topaz','password':'YOUR_QBIT_PASSWORD'}).encode()), timeout=8)
        ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=10).read())
        # Find torrents at 95-99.9% (stuck near completion) 
        stuck = [t for t in ts if t.get('progress',0) >= 0.95 and t.get('progress',0) < 1.0 and t.get('state') in ('stalledDL','pausedDL')]
        if stuck:
            hashes = '|'.join(t['hash'] for t in stuck)
            o.open(urllib.request.Request(f'{url}/api/v2/torrents/resume', data=urllib.parse.urlencode({'hashes':hashes}).encode(), method='POST'), timeout=10)
            for t in stuck: 
                o.open(urllib.request.Request(f'{url}/api/v2/torrents/recheck', data=urllib.parse.urlencode({'hashes':t['hash']}).encode(), method='POST'), timeout=10)
            rescued += len(stuck)
            print(f'  {label}: rescued {len(stuck)} stuck near-complete torrents')
    except Exception as e: print(f'  {label}: {str(e)[:60]}')
if rescued == 0: print('  No stuck torrents found')
"
log "Rescued: done"
