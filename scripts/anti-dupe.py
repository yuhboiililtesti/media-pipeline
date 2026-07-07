#!/usr/bin/env python3
import urllib.request, urllib.parse, json, re, sys, time

LOG = '/mnt/20TB/homelab/media/Pipeline/logs/anti-dupe.log'

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'{ts} {msg}'
    print(line)
    with open(LOG, 'a') as f: f.write(line + '\n')

log('=== anti-dupe scan ===')

for label, url in [('OVERFLOW', 'http://<qbit-overflow-url>'), ('LAPTOP', 'http://<laptop-ip>:8080')]:
    try:
        cj = urllib.request.HTTPCookieProcessor()
        o = urllib.request.build_opener(cj)
        o.open(urllib.request.Request(f'{url}/api/v2/auth/login',
            data=urllib.parse.urlencode({'username':'topaz','password':'YOUR_QBIT_PASSWORD'}).encode()), timeout=10)
        ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=20).read())
        
        groups = {}
        for t in ts:
            name = t['name']
            words = name.lower().replace('.',' ').split()
            prefix = ' '.join(words[:3])
            ep = re.search(r'[Ss](\d{2})[Ee](\d{2})', name)
            year = re.search(r'\b(19|20)\d{2}\b', name)
            if ep:
                key = f"{prefix} S{ep.group(1)}E{ep.group(2)}"
            elif year:
                key = f"{prefix} {year.group(0)}"
            else:
                continue
            if key not in groups: groups[key] = []
            groups[key].append(t)
        
        removed = 0
        for key, torrents in groups.items():
            if len(torrents) > 1:
                best = max(torrents, key=lambda t: (
                    'x265' in t['name'].lower() or 'hevc' in t['name'].lower(),
                    t.get('num_seeds',0), t.get('progress',0)))
                for t in torrents:
                    if t['hash'] != best['hash'] and t.get('state') in ('queuedDL','stalledDL','pausedDL'):
                        try:
                            o.open(urllib.request.Request(f'{url}/api/v2/torrents/delete',
                                data=urllib.parse.urlencode({'hashes': t['hash'], 'deleteFiles': 'true'}).encode(),
                                method='POST'), timeout=10)
                            removed += 1
                        except: pass
        
        if removed > 0:
            log(f'  {label}: removed {removed} dupes')
    except Exception as e:
        log(f'  {label}: error - {str(e)[:80]}')

log('Done')
