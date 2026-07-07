#!/bin/bash
# anti-dupe.sh — Remove duplicate downloads (same show+episode, same movie+year)
# Keeps HEVC/x265 > most seeds > highest progress
# Runs every 30 min via timer
set -euo pipefail

LOG="/mnt/20TB/homelab/media/Pipeline/logs/anti-dupe.log"

log() { echo "$(date '+%H:%M:%S') $1" | tee -a "$LOG"; }

clean_dupes() {
    local label="$1" url="$2"
    
    python3 -c "
import urllib.request, urllib.parse, json, re, sys

try:
    cj = urllib.request.HTTPCookieProcessor()
    o = urllib.request.build_opener(cj)
    o.open(urllib.request.Request('$url/api/v2/auth/login',
        data=urllib.parse.urlencode({'username':'topaz','password':'YOUR_QBIT_PASSWORD'}).encode()), timeout=10)
    ts = json.loads(o.open(urllib.request.Request('$url/api/v2/torrents/info'), timeout=20).read())
    
    groups = {}
    for t in ts:
        name = t['name']
        words = name.lower().replace('.',' ').split()
        prefix = ' '.join(words[:3])
        ep = re.search(r'[Ss](\d{2})[Ee](\d{2})', name)
        year = re.search(r'\b(19|20)\d{2}\b', name)
        
        if ep:
            key = f\"{prefix} S{ep.group(1)}E{ep.group(2)}\"
        elif year:
            key = f\"{prefix} {year.group(0)}\"
        else:
            continue
        
        if key not in groups:
            groups[key] = []
        groups[key].append(t)
    
    removed = 0
    for key, torrents in groups.items():
        if len(torrents) > 1:
            # Keep: x265/HEVC > most seeds > highest progress
            best = max(torrents, key=lambda t: (
                'x265' in t['name'].lower() or 'hevc' in t['name'].lower(),
                t.get('num_seeds',0),
                t.get('progress',0)
            ))
            
            for t in torrents:
                if t['hash'] != best['hash'] and t.get('state') in ('queuedDL','stalledDL','pausedDL'):
                    # Only remove if different release (not different season packs)
                    best_name = best['name'].lower().replace('.',' ')
                    dup_name = t['name'].lower().replace('.',' ')
                    if best_name.split()[0] == dup_name.split()[0]:
                        try:
                            o.open(urllib.request.Request('$url/api/v2/torrents/delete',
                                data=urllib.parse.urlencode({'hashes': t['hash'], 'deleteFiles': 'true'}).encode(),
                                method='POST'), timeout=10)
                            removed += 1
                        except:
                            pass
    
    if removed > 0:
        print(f'  {label}: removed {removed} dupes')
    sys.exit(0)
except Exception as e:
    print(f'  {label}: error - {str(e)[:80]}')
    sys.exit(0)
"
}

log '=== anti-dupe scan ==='
clean_dupes 'OVERFLOW' 'http://127.0.0.1:8083'
clean_dupes 'LAPTOP'  'http://<local-ip>:8080'
log 'Done'
