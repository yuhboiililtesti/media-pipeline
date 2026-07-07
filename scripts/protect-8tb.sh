#!/usr/bin/env python3
# protect-8tb.py v2 — Lock 8TB by setting freeSpace=0 instead of deleting root
# Plex access is UNAFFECTED — it reads filesystem directly
# *arr won't add new content to 8TB, but existing media stays managed

import os, json, urllib.request, time

RADARR_KEY = 'e7746c269b2b43b2a2d102f6dea434e0'
SONARR_KEY = 'YOUR_SONARR_API_KEY'
THRESHOLD = 98
LOG = '/mnt/20TB/homelab/media/Pipeline/logs/protect-8tb.log'

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'{ts} {msg}'
    print(line)
    with open(LOG, 'a') as f: f.write(line + '\n')

s = os.statvfs('/mnt/8TB')
pct = ((s.f_blocks - s.f_bavail) / s.f_blocks) * 100

if pct < THRESHOLD:
    log(f'8TB at {pct:.0f}% — OK (below {THRESHOLD}%)')
    exit(0)

log(f'8TB at {pct:.0f}% — LOCKING (set freeSpace=0, *arr wont add new content)')
log(f'  Plex access is UNAFFECTED — reads filesystem directly')
log(f'  Existing 8TB media stays managed in *arr')

# Lock 8TB roots by setting freeSpace=0 (prevents new downloads, keeps existing content)
for app_name, url, key in [
    ('Radarr', 'http://localhost:7878', RADARR_KEY),
    ('Sonarr', 'http://localhost:8989', SONARR_KEY)
]:
    try:
        r = urllib.request.urlopen(f'{url}/api/v3/rootfolder?apikey={key}', timeout=10)
        roots = json.loads(r.read())
        for root in roots:
            path = root.get('path', '')
            if '/mnt/8TB' in path:
                rid = root['id']
                # Set freeSpace to 0 — *arr treats this as "full" and won't add new content
                update = {'id': rid, 'path': path, 'freeSpace': 0}
                req = urllib.request.Request(
                    f'{url}/api/v3/rootfolder/{rid}?apikey={key}',
                    data=json.dumps(update).encode(),
                    headers={'Content-Type': 'application/json'}, method='PUT')
                urllib.request.urlopen(req, timeout=10)
                log(f'  {app_name}: {path} → locked (freeSpace=0)')
    except Exception as e:
        log(f'  {app_name}: {e}')

log(f'8TB locked. New downloads → 20TB only. Plex reads 8TB normally.')
