#!/usr/bin/env python3
"""Cleanup completed torrents from overflow qBit after Radarr/Sonarr import"""
import urllib.request, urllib.parse, json, time, os

QBIT='http://localhost:8083'; USER='topaz'; PASS='YOUR_QBIT_PASSWORD'
LOG='/mnt/20TB/homelab/media/Pipeline/logs/cleanup-overflow.log'

def log(msg):
    t=time.strftime('%H:%M:%S')
    line='[%s] %s' % (t,msg)
    print(line)
    with open(LOG,'a') as f: f.write(line+chr(10))

log('=== CLEANUP OVERFLOW ===')

c=urllib.request.HTTPCookieProcessor()
o=urllib.request.build_opener(c)
o.open(urllib.request.Request(QBIT+'/api/v2/auth/login',
    data=urllib.parse.urlencode({'username':USER,'password':PASS}).encode()),timeout=8)

ts=json.loads(o.open(urllib.request.Request(QBIT+'/api/v2/torrents/info?filter=completed'),timeout=8).read())
completed=len(ts)

if completed==0:
    exit(0)

# Check if files still exist in download path (if imported by Radarr, file was moved)
removed=0
for t in ts:
    name=t['name']; thash=t['hash']; save_path=t.get('save_path','')+name
    # Check if download still exists
    dl_path='/mnt/20TB/homelab/media/downloads/'+name
    if os.path.exists(dl_path):
        # Also check incomplete
        inc_path='/mnt/20TB/homelab/media/downloads/incomplete/'+name
        if not os.path.exists(inc_path):
            continue  # File exists but not in incomplete — keep seeding
    
    # File was moved/imported — remove torrent
    try:
        o.open(urllib.request.Request(QBIT+'/api/v2/torrents/delete',
            data=urllib.parse.urlencode({'hashes':thash,'deleteFiles':'false'}).encode(),
            method='POST'),timeout=8)
        log('REMOVED: %s' % name[:60])
        removed+=1
        time.sleep(0.3)
    except: pass

if removed>0:
    log('Cleaned %s completed torrents' % removed)
