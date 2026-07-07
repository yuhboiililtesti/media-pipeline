#!/usr/bin/env python3
"""Smart-fill: Auto-queue missing episodes when qBit has room."""
import urllib.request, urllib.parse, json, time, os

QBIT_HOST = '10.0.0.234:8080'; QBIT_USER = 'topaz'; QBIT_PASS = 'YOUR_QBIT_PASSWORD'
SONARR_KEY = 'YOUR_SONARR_API_KEY'; SONARR_URL = 'http://localhost:8989/api/v3'
LOG = '/mnt/20TB/homelab/media/Pipeline/logs/smart-fill.log'
MAX_QUEUED = 150; MAX_PER_RUN = 3

def log(m):
    t = time.strftime('%H:%M:%S')
    l = '[%s] %s' % (t, m)
    print(l)
    with open(LOG, 'a') as f: f.write(l + chr(10))

def qbit_stats():
    try:
        c = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(c)
        d = urllib.parse.urlencode({'username':QBIT_USER,'password':QBIT_PASS}).encode()
        o.open(urllib.request.Request('http://'+QBIT_HOST+'/api/v2/auth/login',data=d),timeout=8)
        ts = json.loads(o.open(urllib.request.Request('http://'+QBIT_HOST+'/api/v2/torrents/info'),timeout=8).read())
        active = len([t for t in ts if t.get('dlspeed',0)>0 or t.get('state')=='downloading'])
        return active, len(ts)
    except Exception as e:
        log('qBit error: %s' % e)
        return 0, 999

log('=== SMART-FILL (existing shows only) ===')
active, total = qbit_stats()
log('qBit: %s active, %s total' % (active, total))
if total >= MAX_QUEUED:
    log('Queue full (%s/%s) - skip' % (total, MAX_QUEUED))
    exit(0)

slots = MAX_QUEUED - total
log('%s slots open - filling missing episodes' % slots)

r = urllib.request.urlopen(SONARR_URL+'/series?apikey='+SONARR_KEY,timeout=15)
shows = json.loads(r.read())

now = int(time.strftime('%Y'))
def rscore(show):
    latest = max([ss.get('year', 0) or 0 for ss in show.get('seasons', [])] + [0])
    return max(0, min(1, float(latest - 2015) / (now - 2015)))

gaps_raw = [(s.get('statistics',{}).get('totalEpisodeCount',0)-s.get('statistics',{}).get('episodeFileCount',0), rscore(s), s['title'], s['id']) for s in shows if s.get('monitored') and s.get('statistics',{}).get('totalEpisodeCount',0)-s.get('statistics',{}).get('episodeFileCount',0)>0]
gaps = sorted(gaps_raw, key=lambda x: x[1]*0.6 + min(x[0]/500,1)*0.4, reverse=True)

log('%s shows have missing episodes (existing shows only)' % len(gaps))
added=0
for gap, _, title, sid in gaps:
    if added>=MAX_PER_RUN: break
    try:
        urllib.request.urlopen(urllib.request.Request(SONARR_URL+'/command?apikey='+SONARR_KEY,data=json.dumps({'name':'SeriesSearch','seriesId':sid}).encode(),headers={'Content-Type':'application/json'},method='POST'),timeout=10)
        log('  Search: %s (%s missing)' % (title, gap))
        added+=1; time.sleep(0.5)
    except: pass
log('Added %s searches' % added)
