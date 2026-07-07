#!/usr/bin/env python3
# protect-20tb.py — Protect 20TB from filling up
# 90% = warn | 95% = slow downloads (med) | 98% = STOP downloads (soft)
# Runs every 30 min

import os, json, urllib.request, time, subprocess

LOG = '/mnt/20TB/homelab/media/Pipeline/logs/protect-20tb.log'

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'{ts} {msg}'
    print(line)
    with open(LOG, 'a') as f: f.write(line + '\n')

def set_pipeline_mode(mode):
    """Switch qBit download limits via pipeline command"""
    try:
        subprocess.run(['/usr/local/bin/pipeline', mode], capture_output=True, timeout=30)
        log(f'  Pipeline set to {mode.upper()} mode')
    except Exception as e:
        log(f'  Pipeline mode switch failed: {e}')

s = os.statvfs('/mnt/20TB')
pct = ((s.f_blocks - s.f_bavail) / s.f_blocks) * 100

if pct < 90:
    log(f'20TB at {pct:.0f}% — OK')
elif pct < 95:
    log(f'20TB at {pct:.0f}% — WARNING: slowing downloads')
    set_pipeline_mode('med')
elif pct < 98:
    log(f'20TB at {pct:.0f}% — CRITICAL: stopping downloads')
    set_pipeline_mode('soft')
else:
    log(f'20TB at {pct:.0f}% — EMERGENCY: downloads halted, root folders disabled')
    set_pipeline_mode('soft')
    # Disable 20TB roots in Radarr/Sonarr
    RADARR_KEY = 'YOUR_RADARR_API_KEY'
    SONARR_KEY = 'YOUR_SONARR_API_KEY'
    
    for app, url, key in [('Radarr', 'http://localhost:7878', RADARR_KEY), 
                           ('Sonarr', 'http://localhost:8989', SONARR_KEY)]:
        try:
            r = urllib.request.urlopen(f'{url}/api/v3/rootfolder?apikey={key}', timeout=10)
            roots = json.loads(r.read())
            for root in roots:
                path = root.get('path', '')
                if '/mnt/20TB' in path:
                    rid = root['id']
                    update = {'id': rid, 'path': path, 'freeSpace': 0}
                    req = urllib.request.Request(
                        f'{url}/api/v3/rootfolder/{rid}?apikey={key}',
                        data=json.dumps(update).encode(),
                        headers={'Content-Type': 'application/json'},
                        method='PUT')
                    try:
                        urllib.request.urlopen(req, timeout=10)
                        log(f'  {app}: {path} -> locked (freeSpace=0)')
                    except urllib.error.HTTPError as e:
                        log(f'  {app} update returned {e.code}')
                    except Exception as e:
                        log(f'  {app}: {e}')
        except Exception as e:
            log(f'  {app} check failed: {e}')
