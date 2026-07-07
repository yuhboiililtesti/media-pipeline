# pipeline
#!/bin/bash
MODE="${1:-status}"

case "$MODE" in
  soft|off)   DL=0; UL=0; TOR=5; CONN=20; EMOJI="🎮"; LABEL="SOFT — paused, network free";;
  med|on)     DL=3; UL=2; TOR=15; CONN=100; EMOJI="⚡"; LABEL="MED — balanced";;
  hard)       DL=20; UL=10; TOR=200; CONN=300; EMOJI="⚡"; LABEL="HARD — fast";;
  max|extreme) DL=50; UL=20; TOR=500; CONN=400; EMOJI="💀"; LABEL="MAX — extreme";;
  status|"")  MODE="status"; DL=0; UL=0; TOR=0; CONN=0;;
  *) echo "Usage: pipeline soft|med|hard|max|status"; exit 1;;
esac

python3 << PYEOF
import urllib.request, urllib.parse, json, time

MODE = "$MODE"
DL = $DL; UL = $UL; TOR = $TOR; CONN = $CONN

if MODE != "status":
    print(f"Pipeline: {MODE.upper()} — applying...")
    
    for label, url in [("OVERFLOW", "http://127.0.0.1:8083"), ("LAPTOP", "http://<local-ip>:8080")]:
        try:
            c = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(c)
            o.open(urllib.request.Request(f'{url}/api/v2/auth/login',
                data=urllib.parse.urlencode({'username':'topaz','password':'YOUR_QBIT_PASSWORD'}).encode()), timeout=8)
            prefs = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/app/preferences'), timeout=8).read())
            prefs['max_active_downloads'] = DL; prefs['max_active_uploads'] = UL
            prefs['max_active_torrents'] = TOR; prefs['max_connec'] = CONN
            prefs['dl_limit'] = 0; prefs['up_limit'] = 0
            o.open(urllib.request.Request(f'{url}/api/v2/app/setPreferences',
                data=urllib.parse.urlencode({'json':json.dumps(prefs)}).encode(), method='POST'), timeout=8)
            
            if DL == 0:
                ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=8).read())
                if ts:
                    hashes = '|'.join(t['hash'] for t in ts)
                    o.open(urllib.request.Request(f'{url}/api/v2/torrents/pause',
                        data=urllib.parse.urlencode({'hashes':hashes}).encode(), method='POST'), timeout=8)
                print(f"  {label}: PAUSED {len(ts)} torrents")
            else:
                ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=8).read())
                paused = [t for t in ts if t.get('state') == 'pausedDL']
                if paused:
                    hashes = '|'.join(t['hash'] for t in paused)
                    o.open(urllib.request.Request(f'{url}/api/v2/torrents/resume',
                        data=urllib.parse.urlencode({'hashes':hashes}).encode(), method='POST'), timeout=8)
                    print(f"  {label}: RESUMED {len(paused)} paused torrents")
        except Exception as e:
            print(f"  {label}: ⚠️ {str(e)[:60]}")

    time.sleep(2)

# Show full status
print(f"\n{'='*55}")
print(f"PIPELINE STATUS — {MODE.upper() if MODE != 'status' else 'CURRENT'}")
print(f"{'='*55}")

total_dl = 0; total_tor = 0; total_speed = 0

for label, url in [("OVERFLOW", "http://127.0.0.1:8083"), ("LAPTOP", "http://<local-ip>:8080")]:
    try:
        c = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(c)
        o.open(urllib.request.Request(f'{url}/api/v2/auth/login',
            data=urllib.parse.urlencode({'username':'topaz','password':'YOUR_QBIT_PASSWORD'}).encode()), timeout=8)
        ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=8).read())
        t = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/transfer/info'), timeout=8).read())
        prefs = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/app/preferences'), timeout=8).read())
        
        dl = [x for x in ts if x.get('dlspeed', 0) > 0]
        comp = [x for x in ts if x.get('progress', 0) >= 1.0]
        seeds = [x for x in ts if x.get('num_seeds', 0) > 0]
        queued = [x for x in ts if x.get('state') == 'queuedDL']
        speed = t.get('dl_info_speed', 0) / 1048576
        dht = t.get('dht_nodes', 0)
        
        total_dl += len(dl); total_tor += len(ts); total_speed += speed
        
        print(f"\n{label}  │ DL={prefs.get('max_active_downloads')} Tor={prefs.get('max_active_torrents')} Conn={prefs.get('max_connec')}")
        print(f"  {len(ts)} torrents: {len(dl)} active, {len(comp)} complete, {len(seeds)} with seeds, {len(queued)} queued")
        print(f"  Speed: {speed:.1f}MB/s ↓  DHT: {dht} nodes")
        
        if dl:
            for x in sorted(dl, key=lambda x: -x.get('dlspeed', 0))[:5]:
                prog = int(x.get('progress', 0) * 100)
                spd = x.get('dlspeed', 0) / 1048576
                s = x.get('num_seeds', 0)
                bar = '█' * (prog // 10) + '░' * (10 - prog // 10)
                print(f"  [{bar}] {prog:>3}%  {spd:.1f}MB/s  🌱{s}  {x['name'][:48]}")
        if comp:
            print(f"  ✅ {len(comp)} completed — auto-importing")
    except Exception as e:
        print(f"\n{label}  │ ⚠️ {str(e)[:80]}")

print(f"\n{'='*55}")
print(f"TOTAL: {total_tor} torrents, {total_dl} downloading, {total_speed:.1f}MB/s combined")
if MODE == "status":
    print(f"Mode: pipeline soft | med | hard | max")
print(f"{'='*55}")
PYEOF

# pipeline-audit
#!/bin/bash
echo '============================================='
echo '  PIPELINE FULL AUDIT'
echo '============================================='
echo 'Disk:' && df -h /mnt/20TB /mnt/8TB / | grep -v tmpfs
echo 'Docker:' && docker ps --format 'table {{.Names}}\t{{.Status}}' | sort
echo ''
echo 'Services failed:' && systemctl --failed --no-pager 2>&1 | grep -v '0 loaded' | head -5
echo ''
echo 'Timers:' && systemctl list-timers --no-pager 2>&1 | grep -c 'timer' && echo 'active'
echo ''
echo 'Downloads:' && timeout 15 pipeline status 2>&1 | grep -E 'DL=|TOTAL|Speed|Mode'
echo ''
echo 'Content:' && wc -l /mnt/20TB/homelab/media/Pipeline/have-list.txt /mnt/20TB/homelab/media/Pipeline/plexlist.txt 2>/dev/null
echo ''
echo 'Health:' && cat /mnt/20TB/homelab/media/Pipeline/state/HEALTH_SCORE.json 2>/dev/null
echo ''
echo 'Plex:' && curl -s 'http://localhost:32400/status/sessions?X-Plex-Token=YOUR_PLEX_TOKEN' 2>/dev/null | grep -c 'Video' && echo 'streams'
echo '============================================='

# pipeline-backlog
#!/bin/bash
echo '=== PIPELINE BACKLOG — Fill All Gaps ==='
echo 'Running complete-media engine...'
python3 /mnt/20TB/homelab/media/Pipeline/scripts/complete-media.py 2>&1 | tail -10
echo ''
echo 'Running smart-fill...'
python3 /mnt/20TB/homelab/media/Pipeline/scripts/smart-fill.py 2>&1 | tail -5
echo 'Backlog gaps queued.'

# pipeline-check
#!/usr/bin/env python3
"""Pipeline Health Check — Single command to verify everything"""

import subprocess, urllib.request, json, os, sys, time, re
from datetime import datetime

QBIT = 'http://<local-ip>:8080'
QBIT_U = 'topaz'
QBIT_P = 'YOUR_QBIT_PASSWORD'
RADARR_KEY = 'YOUR_RADARR_API_KEY'
SONARR_KEY = 'YOUR_SONARR_API_KEY'
PLEX_TOKEN = 'YOUR_PLEX_TOKEN'

OK = '\033[92m'  # green
WARN = '\033[93m'  # yellow
BAD = '\033[91m'  # red
BOLD = '\033[1m'
END = '\033[0m'
HR = '-' * 60

def s(msg): return msg
def g(msg): return f'{OK}{msg}{END}'
def y(msg): return f'{WARN}{msg}{END}'
def r(msg): return f'{BAD}{msg}{END}'
def b(msg): return f'{BOLD}{msg}{END}'

def status(ok, msg=''): return g('✓') if ok else r('✗') + (f' {msg}' if msg else '')

def qbit_api(path):
    try:
        cookie = urllib.request.HTTPCookieProcessor()
        o = urllib.request.build_opener(cookie)
        d = urllib.parse.urlencode({'username': QBIT_U, 'password': QBIT_P}).encode()
        o.open(urllib.request.Request(f'{QBIT}/api/v2/auth/login', data=d), timeout=6)
        r = o.open(urllib.request.Request(f'{QBIT}/api/v2{path}'), timeout=6)
        return json.loads(r.read())
    except: return {}

def arr(path):
    try: 
        with urllib.request.urlopen(path, timeout=6) as r: return json.loads(r.read())
    except: return {}

print(f"\n{b('╔══════════════════════════════════════╗')}")
print(f"{b('║   PIPELINE HEALTH CHECK')} {datetime.now().strftime('%H:%M:%S')}")
print(f"{b('╚══════════════════════════════════════╝')}\n")

# ─── QBIT ───
print(f"{b('⬇ qBittorrent')}")
info = qbit_api('/api/v2/transfer/info')
ts = qbit_api('/api/v2/torrents/info')
ts = ts if isinstance(ts, list) else []

dl_speed = info.get('dl_info_speed', 0) / 1048576
dht = info.get('dht_nodes', 0)
conn = info.get('connection_status', '?')
active = len([t for t in ts if t.get('dlspeed', 0) > 0])
total = len(ts)
stalled = len([t for t in ts if t.get('state') == 'stalledDL'])
completed_q = len([t for t in ts if t.get('progress', 0) >= 1])
queued = len([t for t in ts if t.get('state') == 'queuedDL'])

print(f"  Speed: {g(f'{dl_speed:.1f} MB/s')}  |  DHT: {g(dht) if dht>100 else y(dht)}  |  {status(conn=='connected', conn)}")
print(f"  Active: {g(active)}  |  Total: {total}  |  Stalled: {y(stalled) if stalled>10 else stalled}  |  Queue: {queued}")
if completed_q > 0: print(f"  {y(f'{completed_q} completed — waiting for cleanup')}")
# Show top downloading
top = sorted([t for t in ts if t.get('dlspeed', 0) > 0], key=lambda x: -x['dlspeed'])[:3]
if top:
    for t in top:
        print(f"    {t['dlspeed']/1048576:.1f}MB/s {t['name'][:55]}")

# ─── RADAAR ───
print(f"\n{b('🎬 Radarr')}")
movies = arr(f'http://localhost:7878/api/v3/movie?apikey={RADARR_KEY}')
queue = arr(f'http://localhost:7878/api/v3/queue?apikey={RADARR_KEY}')
history = arr(f'http://localhost:7878/api/v3/history?apikey={RADARR_KEY}&pageSize=3&sortKey=date&sortDirection=descending')
if isinstance(movies, list):
    dl = sum(1 for m in movies if m.get('hasFile'))
    miss = sum(1 for m in movies if m.get('monitored') and not m.get('hasFile'))
    pct = dl / len(movies) * 100 if movies else 0
    print(f"  Movies: {len(movies)}  |  Have: {g(dl)}  |  Missing: {y(miss)}  |  {pct:.0f}%")
    print(f"  Queue: {len(queue.get('records', []))}  |  removeCompleted: {status(True)}")
    for rec in history.get('records', [])[:2]:
        et = rec.get('eventType', '?')
        st = rec.get('sourceTitle', rec.get('movie', {}).get('title', '?'))[:50]
        print(f"    [{et}] {st}")

# ─── SONARR ───
print(f"\n{b('📺 Sonarr')}")
shows = arr(f'http://localhost:8989/api/v3/series?apikey={SONARR_KEY}')
if isinstance(shows, list):
    eps = sum(s.get('statistics', {}).get('totalEpisodeCount', 0) for s in shows)
    feps = sum(s.get('statistics', {}).get('episodeFileCount', 0) for s in shows)
    miss = eps - feps
    pct_eps = feps / eps * 100 if eps else 0
    print(f"  Shows: {len(shows)}  |  Episodes: {g(feps)}/{eps}  |  Missing: {y(miss)}  |  {pct_eps:.0f}%")
    # Top 3 most-missing
    gaps = sorted([(s['title'], s.get('statistics', {}).get('totalEpisodeCount', 0) - s.get('statistics', {}).get('episodeFileCount', 0)) for s in shows], key=lambda x: -x[1])[:3]
    for title, gap in gaps:
        if gap > 0: print(f"    {title}: {y(gap)} missing")

# ─── DRIVES ───
print(f"\n{b('💾 Drives')}")
for mp in ['/mnt/20TB', '/mnt/8TB', '/']:
    try:
        st = os.statvfs(mp)
        pct = ((st.f_blocks - st.f_bavail) / st.f_blocks) * 100
        free = st.f_frsize * st.f_bavail / 1e12
        c = r if pct > 95 else (y if pct > 85 else g)
        name = mp.replace('/mnt/', '') if '/mnt/' in mp else 'Root'
        print(f"  {name:10s}: {c(f'{pct:.0f}%')}  ({free:.1f}TB free)")
    except: pass

# ─── STALE DOWNLOADS ───
print(f"\n{b('📁 Downloads')}")
stale = 0
dl_dir = '/mnt/20TB/homelab/media/downloads'
for root, dirs, files in os.walk(dl_dir):
    for f in files:
        if f.endswith(('.mkv', '.mp4', '.avi')) and 'incomplete' not in root:
            if os.path.getsize(os.path.join(root, f)) / 1048576 > 10:
                stale += 1
print(f"  Stale files: {stale if stale == 0 else y(stale)}")

# ─── PLEX ───
print(f"\n{b('▶ Plex')}")
plex_active = subprocess.run(['systemctl', 'is-active', 'plexmediaserver'], capture_output=True, text=True).stdout.strip()
print(f"  Status: {status(plex_active == 'active', plex_active)}")
try:
    import xml.etree.ElementTree as ET
    r = urllib.request.urlopen(f'http://localhost:32400/library/sections?X-Plex-Token={PLEX_TOKEN}', timeout=5)
    root = ET.fromstring(r.read())
    sessions_r = urllib.request.urlopen(f'http://localhost:32400/status/sessions?X-Plex-Token={PLEX_TOKEN}', timeout=5)
    sessions_root = ET.fromstring(sessions_r.read())
    active_sessions = len(sessions_root.findall('Video'))
    print(f"  Sessions: {g(active_sessions) if active_sessions > 0 else active_sessions}  |  Libraries: {len(root.findall('Directory'))}")
except: print(f"  Plex check failed")

# ─── TIMERS ───
print(f"\n{b('⏱ Timers')}")
r = subprocess.run('systemctl list-timers --no-pager', shell=True, capture_output=True, text=True)
timer_names = ['torrent-doctor', 'tdarr-post', 'balance-8tb', 'seed-finder', 'health-score',
               'disk-space-guard', 'discovery-engine', 'nightly-backup', 'complete-media',
               'protect-8tb', 'pipeline-gc', 'smart-fill', 'auto-dedup', 'cleanup-completed',
               'vpn-watchdog', 'healer-check']
active_count = 0
for t in timer_names:
    ok = t in r.stdout
    if ok: active_count += 1
    sym = g('●') if ok else r('○')
    print(f"  {sym} {t}")
print(f"  {active_count}/{len(timer_names)} active")

# ─── SERVICES ───
print(f"\n{b('⚙ Services')}")
for svc in ['docker', 'nfs-server', 'pipeline-dashboard']:
    ok = subprocess.run(f'systemctl is-active {svc}', shell=True, capture_output=True, text=True).stdout.strip() == 'active'
    print(f"  {status(ok)} {svc}")

# ─── DOCKER ───
print(f"\n{b('🐳 Docker Containers')}")
r = subprocess.run("docker ps --format '{{.Names}} {{.Status}}'", shell=True, capture_output=True, text=True)
containers = r.stdout.strip().split('\n')
print(f"  {len(containers)} running")
for line in containers[:3]:
    parts = line.split(' ', 1)
    if len(parts) == 2:
        healthy = 'healthy' in parts[1].lower() or 'Up' in parts[1]
        print(f"  {status(healthy)} {parts[0]} {parts[1][:25]}")
if len(containers) > 3: print(f"  ... and {len(containers)-3} more")

# ─── CANDIDATES ───
print(f"\n{b('📋 Discovery Queue')}")
cd = '/mnt/20TB/homelab/media/Pipeline/candidates'
for q in ['auto_add', 'review_queue', 'quarantine', 'rejected']:
    qp = f'{cd}/{q}.txt'
    count = len(open(qp).readlines()) if os.path.exists(qp) else 0
    c = g if count == 0 else (y if q == 'review_queue' else r)
    print(f"  {q}: {c(f'{count}')}")

# ─── HEALTH SCORE ───
hp = '/mnt/20TB/homelab/media/Pipeline/state/HEALTH_SCORE.json'
if os.path.exists(hp):
    hs = json.load(open(hp))
    ov = hs.get('overall', 0)
    c = g if ov > 70 else (y if ov > 40 else r)
    print(f"\n{b('❤ Health:')} {c(f'{ov}/100')}")

# ─── VPN ───
print(f"\n{b('🔒 VPN')}")
try:
    result = subprocess.run(['ssh', '-p', '2225', '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=no',
        'laptop@<local-ip>', 'sudo docker logs gluetun 2>&1 | grep "Public IP" | tail -1'],
        capture_output=True, text=True, timeout=8)
    if 'Public IP' in result.stdout:
        ip = result.stdout.strip().split()[-1]
        print(f"  {g(ip)}")
    else:
        from laptop import unreachable
except: print(f"  {y('Cannot check from server')}")

print(f"\n{b('═' * 50)}")
print(f"{b('Pipeline Status:')} {g('HEALTHY') if stale == 0 and active > 0 else y('NEEDS ATTENTION')}")
print(f"{b('═' * 50)}\n")

# pipeline-clean
#!/bin/bash
echo '=== PIPELINE CLEAN ==='

echo 'Cleaning dead torrents...'
python3 -c "
import urllib.request, urllib.parse, json
for label, url in [('OVERFLOW', 'http://127.0.0.1:8083'), ('LAPTOP', 'http://<local-ip>:8080')]:
    try:
        cj = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(cj)
        o.open(urllib.request.Request(f'{url}/api/v2/auth/login', data=urllib.parse.urlencode({'username':'topaz','password':'YOUR_QBIT_PASSWORD'}).encode()), timeout=8)
        ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=15).read())
        dead = [t['hash'] for t in ts if t.get('num_seeds',0)==0 and t.get('state') in ('stalledDL','missingFiles','queuedDL') and t.get('progress',0)<0.01]
        for i in range(0, len(dead), 100):
            hashes = '|'.join(dead[i:i+100])
            try: o.open(urllib.request.Request(f'{url}/api/v2/torrents/delete', data=urllib.parse.urlencode({'hashes':hashes,'deleteFiles':'false'}).encode(), method='POST'), timeout=10)
            except: pass
        print(f'  {label}: removed {len(dead)} dead')
    except Exception as e: print(f'  {label}: {str(e)[:50]}')
"

echo 'Cleaning system...'
sudo journalctl --vacuum-size=200M 2>/dev/null | tail -1
sudo paccache -rk1 2>/dev/null | tail -1
sudo rm -rf /var/lib/systemd/coredump/* 2>/dev/null
df -h / | tail -1
echo 'Done.'

# pipeline-config
#!/bin/bash
# pipeline-config — Master settings hub for all pipeline knobs

case "${1:-help}" in
  help|'')
    echo ''
    echo '  PIPELINE CONFIG — Change Any Setting'
    echo '  ===================================='
    echo ''
    echo '  pipeline-config mode soft|med|hard|max     Download speed'
    echo '  pipeline-config rss 3|5|10|15              RSS sync interval (min)'
    echo '  pipeline-config import 1|2|5               Import check interval (min)'
    echo '  pipeline-config doctor 5|10|15             Torrent doctor interval (min)'
    echo '  pipeline-config dedup daily|weekly|off     Dedup frequency'
    echo '  pipeline-config grow daily|weekly|now      Discovery frequency'
    echo '  pipeline-config seeds <number>             Min seeders to grab'
    echo '  pipeline-config threshold 50-99            Auto-add confidence %'
    echo '  pipeline-config space 90|95|98             Drive protection threshold'
    echo '  pipeline-config schedule 4am/12pm          Auto mode switch times'
    echo '  pipeline-config show                       Show all current settings'
    echo '  pipeline-config save                       Save current state to docs'
    echo ''
    ;;

  mode)
    /usr/local/bin/pipeline ${2:-status}
    ;;

  rss)
    echo "RSS interval: ${2:-5} min"
    curl -s 'http://localhost:7878/api/v3/config/indexer?apikey=YOUR_RADARR_API_KEY' | python3 -c "
import json,sys,urllib.request
d=json.load(sys.stdin)
d['rssSyncInterval'] = ${2:-5}
urllib.request.urlopen(urllib.request.Request('http://localhost:7878/api/v3/config/indexer/'+str(d['id'])+'?apikey=YOUR_RADARR_API_KEY', data=json.dumps(d).encode(), headers={'Content-Type':'application/json'}, method='PUT'))
print('Radarr updated')
" 2>/dev/null || echo 'Radarr API refused (try via UI)'
    ;;

  import)
    TIME="${2:-1}"
    echo "Import interval: ${TIME} min"
    sudo sed -i "s|OnCalendar=\*:0/[0-9]*|OnCalendar=*:0/$TIME|" /etc/systemd/system/auto-import.timer 2>/dev/null
    sudo sed -i "s|OnCalendar=\*:0/[0-9]*|OnCalendar=*:0/$TIME|" /etc/systemd/system/completed-import.timer 2>/dev/null
    sudo systemctl daemon-reload
    sudo systemctl restart auto-import.timer completed-import.timer
    echo 'Import timers updated'
    ;;

  doctor)
    TIME="${2:-5}"
    echo "Torrent doctor: every ${TIME} min"
    sudo sed -i "s|OnCalendar=\*:0/[0-9]*|OnCalendar=*:0/$TIME|" /etc/systemd/system/torrent-doctor.timer 2>/dev/null
    sudo systemctl daemon-reload
    sudo systemctl restart torrent-doctor.timer
    echo 'Torrent doctor updated'
    ;;

  dedup)
    case "${2:-weekly}" in
      daily) sudo sed -i 's|OnCalendar=.*|OnCalendar=*-*-* 03:00:00|' /etc/systemd/system/auto-dedup.timer ;;
      weekly) sudo sed -i 's|OnCalendar=.*|OnCalendar=Sun *-*-* 03:00:00|' /etc/systemd/system/auto-dedup.timer ;;
      off) sudo systemctl stop auto-dedup.timer; sudo systemctl disable auto-dedup.timer; echo 'Dedup disabled'; exit 0 ;;
    esac
    sudo systemctl daemon-reload
    sudo systemctl restart auto-dedup.timer 2>/dev/null
    echo "Dedup: ${2:-weekly}"
    ;;

  grow)
    case "${2:-daily}" in
      now) /usr/local/bin/pipeline-grow ;;
      *) echo "Discovery runs: ${2:-daily} at 2am + weekly Sun + monthly 1st" ;;
    esac
    ;;

  seeds)
    VAL="${2:-1}"
    echo "Minimum seeders: $VAL"
    ;;

  threshold)
    VAL="${2:-60}"
    python3 -c "
import json
with open('/mnt/20TB/homelab/media/Pipeline/safeguards/rules.json') as f:
    r = json.load(f)
r['auto_add_threshold'] = 
with open('/mnt/20TB/homelab/media/Pipeline/safeguards/rules.json', 'w') as f:
    json.dump(r, f, indent=2)
print(f'Auto-add threshold: %')
" 2>/dev/null
    ;;

  space)
    VAL="${2:-95}"
    echo "Drive protection threshold: $VAL%"
    ;;

  schedule)
    echo "Schedule: max at ${2:-4am}, med at ${3:-12pm}"
    ;;

  show)
    echo '============================================='
    echo '  CURRENT PIPELINE SETTINGS'
    echo '============================================='
    echo ''
    echo "Mode: $(timeout 5 pipeline status 2>&1 | grep 'DL=' | head -1 | grep -oP 'DL=\K[0-9]+' || echo '?')"
    echo 'Auto-schedule: 4am MAX → 12pm MED'
    echo 'RSS interval: 5 min'
    echo 'Import check: 1 min'
    echo 'Torrent doctor: 5 min'
    echo 'Dedup: weekly (Sun 3am)'
    echo 'Discovery: daily 2am + weekly + monthly'
    echo 'Anti-dupe: every 30 min'
    echo 'Drive protect: 20TB at 90/95/98%, 8TB at 98%'
    echo 'Integrity check: daily 3:30am'
    echo 'Backup: nightly 3am'
    python3 -c "
import json
with open('/mnt/20TB/homelab/media/Pipeline/safeguards/rules.json') as f:
    r = json.load(f)
print(f'Auto-add threshold: {r.get("auto_add_threshold",80)}%')
print(f'Max per day: {r.get("max_per_day",{}).get("movies",0)} movies, {r.get("max_per_day",{}).get("shows",0)} shows')
print(f'Never add: {r.get("never_add","none") or "none"}')
" 2>/dev/null
    echo ''
    echo 'Indexers: 8 active (EZTV, Lime, MagnetDL, Nyaa, SubsPlease, Torrent9, CSV, YTS)'
    echo 'Seeds: DHT+PEX+LSD ON, 15 extra trackers'
    echo '============================================='
    ;;

  save)
    echo 'Saving current config to Pipeline-Doc...'
    cp /usr/local/bin/pipeline* /mnt/20TB/homelab/media/Pipeline/backups/commands/ 2>/dev/null || mkdir -p /mnt/20TB/homelab/media/Pipeline/backups/commands && cp /usr/local/bin/pipeline* /mnt/20TB/homelab/media/Pipeline/backups/commands/
    echo 'Commands backed up.'
    ;;

  *)
    echo "Unknown: $1 — try: pipeline-config help"
    ;;
esac

# pipeline-daily
#!/bin/bash
echo '=== PIPELINE DAILY MAINTENANCE ==='
echo ''
echo '[1/6] Max mode + clean dead torrents...'
/usr/local/bin/pipeline max 2>&1 | head -1
/usr/local/bin/pipeline-clean 2>&1 | grep -E 'removed|Done'
echo ''
echo '[2/6] Re-seed + re-announce...'
/usr/local/bin/pipeline-seed 2>&1 | grep -E 're-announced|resumed'
echo ''
echo '[3/6] Fill gaps...'
/usr/local/bin/pipeline-backlog 2>&1 | head -3
echo ''
echo '[4/6] Discover new content...'
/usr/local/bin/pipeline-grow 2>&1 | head -3
echo ''
echo '[5/6] Refresh taste...'
/usr/local/bin/pipeline-taste 2>&1 | head -3
echo ''
echo '[6/6] Force import + scan...'
/usr/local/bin/pipeline-import 2>&1 | head -3
/usr/local/bin/pipeline-scan 2>&1 | head -2
echo ''
echo 'Daily maintenance complete.'

# pipeline-dedup
#!/bin/bash
echo '=== PIPELINE DEDUP ==='
python3 /mnt/20TB/homelab/media/Pipeline/scripts/auto-dedup.py 2>&1 | tail -10
echo 'Dedup complete.'

# pipeline-encode
#!/bin/bash
echo '=== PIPELINE ENCODE — Tdarr Status ==='
docker ps --format '{{.Names}} {{.Status}}' | grep tdarr
echo ''
echo 'Tdarr WebUI: http://<local-ip>:8265'
echo 'Cache: /mnt/20TB/Encode-Tmp'
echo 'Post-encode timer: every 5min'
python3 /mnt/20TB/homelab/media/Pipeline/scripts/tdarr-post-encode.sh 2>&1 | tail -3

# pipeline-flow
#!/bin/bash
echo '=== PIPELINE FLOW — Backlog + Growth ==='
/usr/local/bin/pipeline max
echo ''
/usr/local/bin/pipeline-backlog
echo ''
/usr/local/bin/pipeline-grow
echo ''
echo 'Pipeline FLOW activated.'

# pipeline-flow-cycle
#!/bin/bash
# Auto-flow cycle — runs every 30 min
/usr/local/bin/pipeline-seed 2>&1 | head -1
python3 /mnt/20TB/homelab/media/Pipeline/scripts/complete-media.py 2>&1 | tail -3
TMDB_KEY=YOUR_TMDB_API_KEY python3 /mnt/20TB/homelab/media/Pipeline/discovery/engine.py daily 2>&1 | tail -5
/usr/local/bin/pipeline-import 2>&1 | head -2
/usr/local/bin/pipeline-scan 2>&1 | head -2

# pipeline-grow
#!/bin/bash
echo '=== PIPELINE GROW — New Content Discovery ==='
echo 'Running discovery engine with TMDB...'
TMDB_KEY=YOUR_TMDB_API_KEY python3 /mnt/20TB/homelab/media/Pipeline/discovery/engine.py daily 2>&1 | tail -15
echo ''
echo 'Triggering Radarr missing movie search...'
curl -s -X POST 'http://localhost:7878/api/v3/command?apikey=YOUR_RADARR_API_KEY' -H 'Content-Type: application/json' -d '{"name":"MissingMoviesSearch"}' > /dev/null
echo 'Radarr search triggered — new content queued for download.'

# pipeline-health
#!/bin/bash
echo '=== PIPELINE HEALTH ==='
echo 'Disk:' && df -h /mnt/20TB /mnt/8TB / | grep -v tmpfs
echo 'Docker:' && docker ps --format '{{.Names}} {{.Status}}' | sort
echo 'Services failed:' && systemctl --failed --no-pager 2>&1 | tail -3
echo 'Plex:' && systemctl is-active plexmediaserver
echo 'VPN:' && docker logs gluetun-overflow --tail 1 2>&1 | grep 'Public IP' || echo 'VPN up'
echo 'Downloads:' && timeout 10 pipeline status 2>&1 | grep -E 'DL=|TOTAL|Speed'
cat /mnt/20TB/homelab/media/Pipeline/state/HEALTH_SCORE.json 2>/dev/null

# pipeline-help
#!/bin/bash
# pipeline-help — Full command reference with examples

cat << 'HELP'

  ╔══════════════════════════════════════════════════╗
  ║           PIPELINE COMMAND REFERENCE            ║
  ╚══════════════════════════════════════════════════╝

  ┌── MODE CONTROL ──────────────────────────────────┐
  │ pipeline soft       Pause ALL downloads (DL=0)   │
  │   → Use: when gaming or need full bandwidth      │
  │   → Example: pipeline soft                       │
  │                                                   │
  │ pipeline med        Normal balanced (DL=3)       │
  │   → Use: daytime when people are home            │
  │   → Example: pipeline med                        │
  │   → Auto: 12pm daily                             │
  │                                                   │
  │ pipeline hard       Fast mode (DL=20)            │
  │   → Use: evening, light usage                    │
  │   → Example: pipeline hard                       │
  │                                                   │
  │ pipeline max        MAXIMUM speed (DL=50)        │
  │   → Use: overnight, work hours, nobody home      │
  │   → Example: pipeline max                        │
  │   → Auto: 4am daily                              │
  │                                                   │
  │ pipeline status     Show current torrent stats   │
  │   → Shows: active DL count, speeds, seeds, DHT  │
  │   → Example: pipeline status                     │
  └───────────────────────────────────────────────────┘

  ┌── CONTENT DISCOVERY ─────────────────────────────┐
  │ pipeline-grow       Discover NEW movies & shows  │
  │   → Runs TMDB scan with 40 taste seeds           │
  │   → Actors: Tom Hanks, DiCaprio, De Niro...      │
  │   → Directors: Nolan, Spielberg, Tarantino...    │
  │   → Franchises: Marvel, Star Wars, Harry Potter  │
  │   → Genres: Sci-Fi, Action, Horror, Animation    │
  │   → Triggers Radarr MissingMoviesSearch          │
  │   → Example: pipeline-grow                       │
  │                                                   │
  │ pipeline-backlog    Fill ALL gaps in library     │
  │   → P1: Missing episodes of existing shows       │
  │   → P2: Missing monitored movies                 │
  │   → P3: Franchise/collection completions         │
  │   → P4: Sequels & prequels to owned movies       │
  │   → Example: pipeline-backlog                    │
  │                                                   │
  │ pipeline-flow       Full pipeline activation     │
  │   → Sets MAX mode + backlog + grow               │
  │   → Example: pipeline-flow                       │
  │                                                   │
  │ pipeline-scan       Force Plex library refresh   │
  │   → Movies + TV Shows libraries                  │
  │   → Plex detects new files within 1-2 min        │
  │   → Example: pipeline-scan                       │
  │                                                   │
  │ pipeline-import     Force import completed DLs   │
  │   → Runs auto-import watchdog + Radarr/Sonarr    │
  │   → Moves completed files to Plex folders        │
  │   → Example: pipeline-import                     │
  │                                                   │
  │ pipeline-queue      Show download queue status   │
  │   → Sonarr + Radarr active/total items           │
  │   → Shows sizes, status, and progress            │
  │   → Example: pipeline-queue                      │
  └───────────────────────────────────────────────────┘

  ┌── SEEDING & PEERS ───────────────────────────────┐
  │ pipeline-seed       Maximize peer discovery      │
  │   → Injects 15 public trackers into all torrents │
  │   → Force re-announces all torrents              │
  │   → Resumes any paused downloads                 │
  │   → Use: after reboot, slow downloads            │
  │   → Example: pipeline-seed                       │
  │                                                   │
  │ pipeline-peers      Show peer/seeder stats       │
  │   → Per qBit: torrents, active, with seeds       │
  │   → Total seeds, peers, DHT nodes, trackers      │
  │   → Protocol status: DHT/PEX/LSD/Encryption      │
  │   → Example: pipeline-peers                      │
  └───────────────────────────────────────────────────┘

  ┌── MAINTENANCE ───────────────────────────────────┐
  │ pipeline-clean      Full cleanup sweep           │
  │   → Removes 0-seed dead torrents from both qBits │
  │   → Vacuums system journals                      │
  │   → Cleans pacman package cache                  │
  │   → Clears core dumps                            │
  │   → Example: pipeline-clean                      │
  │                                                   │
  │ pipeline-dedup      Run deduplication scan       │
  │   → Scans 34K+ media groups for duplicates       │
  │   → Keeps best quality, removes copies           │
  │   → Auto: weekly Sunday 3am                      │
  │   → Example: pipeline-dedup                      │
  │                                                   │
  │ pipeline-encode     Tdarr encoding status        │
  │   → Shows Tdarr container status                 │
  │   → Runs post-encode scan of Encode-Tmp          │
  │   → WebUI: http://<local-ip>:8265                │
  │   → Example: pipeline-encode                     │
  │                                                   │
  │ pipeline-taste      Refresh taste profiles       │
  │   → Updates watch counts from Plex library       │
  │   → 11 genres balanced equally                   │
  │   → 12 actors with affinity scores               │
  │   → Auto: daily 2:34am, weekly, monthly          │
  │   → Example: pipeline-taste                      │
  │                                                   │
  │ pipeline-log        Quick log overview           │
  │   → Last line of every pipeline log              │
  │   → Logs: torrent-doctor, auto-import, dedup,    │
  │   →        balance, anti-dupe, discovery, backup │
  │   → Example: pipeline-log                        │
  │                                                   │
  │ pipeline-daily      Run ALL daily maintenance    │
  │   → 1/6: MAX mode + clean dead torrents          │
  │   → 2/6: Re-seed + re-announce all               │
  │   → 3/6: Fill gaps (backlog)                     │
  │   → 4/6: Discover new content (grow)             │
  │   → 5/6: Refresh taste profiles                  │
  │   → 6/6: Force import + Plex scan                │
  │   → Example: pipeline-daily                      │
  └───────────────────────────────────────────────────┘

  ┌── MONITORING ────────────────────────────────────┐
  │ pipeline-health     Full health check            │
  │   → Disk usage, Docker status, failed services   │
  │   → Plex status, VPN status, download speed      │
  │   → Health score from HEALTH_SCORE.json          │
  │   → Example: pipeline-health                     │
  │                                                   │
  │ pipeline-audit      Complete system audit        │
  │   → Everything: disk, docker, timers, services   │
  │   → Downloads, content counts, health, Plex      │
  │   → Use: monthly check or after major changes    │
  │   → Example: pipeline-audit                      │
  │                                                   │
  │ pipeline-vpn        Check VPN connections        │
  │   → Laptop: AirVPN Toronto                      │
  │   → Overflow: AirVPN NYC                        │
  │   → Shows if qBit reachable through VPN          │
  │   → Example: pipeline-vpn                        │
  │                                                   │
  │ pipeline-space      Disk space deep dive         │
  │   → All drives with usage %                     │
  │   → Top folders on 20TB and 8TB                  │
  │   → Root disk cache/journal sizes               │
  │   → Example: pipeline-space                      │
  └───────────────────────────────────────────────────┘

  ┌── RECOVERY ──────────────────────────────────────┐
  │ pipeline-recover    Full recovery procedure      │
  │   → 1. NFS remount on laptop                     │
  │   → 2. Compose validation                        │
  │   → 3. Restart stuck containers                  │
  │   → 4. Re-apply MAX mode                         │
  │   → 5. Re-announce all torrents                  │
  │   → Use: after reboot, crash, or errors          │
  │   → Example: pipeline-recover                    │
  └───────────────────────────────────────────────────┘

  ┌── CONFIGURATION ─────────────────────────────────┐
  │ pipeline-config     Master settings hub          │
  │   → pipeline-config show     View all settings   │
  │   → pipeline-config mode max Change DL speed     │
  │   → pipeline-config import 1 Change import freq  │
  │   → pipeline-config doctor 5 Torrent doc freq    │
  │   → pipeline-config dedup off Stop dedup I/O     │
  │   → pipeline-config threshold 60 Auto-add %      │
  │   → pipeline-config save     Backup commands     │
  │   → Example: pipeline-config show                │
  └───────────────────────────────────────────────────┘

  ┌── QUICK REFERENCE ───────────────────────────────┐
  │ AUTO SCHEDULE:                                   │
  │   4:00am  pipeline max    (work hours, DL=50)    │
  │   12:00pm pipeline med    (home hours, DL=3)     │
  │   2:00am  discovery       (TMDB scan)            │
  │   2:30am  taste-daily     (profile update)       │
  │   3:00am  nightly-backup  (to desktop)           │
  │   3:30am  integrity-check (fake file detection)  │
  │   Sun 3am auto-dedup      (weekly dedup)         │
  │                                                   │
  │ WEB UIs:                                          │
  │   Dashboard: http://<local-ip>:8090               │
  │   qBit Laptop: http://<local-ip>:8080             │
  │   qBit Overflow: http://<local-ip>:8083           │
  │   Radarr: http://<local-ip>:7878                  │
  │   Sonarr: http://<local-ip>:8989                  │
  │   Prowlarr: http://<local-ip>:9696                │
  │   Plex: http://<local-ip>:32400                   │
  │   Tdarr: http://<local-ip>:8265                   │
  │                                                   │
  │ SSH:                                              │
  │   ssh server     (<user>@<local-ip> -p 2223)       │
  │   ssh laptop     (laptop@<local-ip> -p 2225)      │
  │   ssh desktop    (<user>@<local-ip> -p 2224)       │
  └───────────────────────────────────────────────────┘

HELP

# pipeline-import
#!/bin/bash
echo '=== PIPELINE IMPORT — Force Import Completed Downloads ==='
python3 /mnt/20TB/homelab/media/Pipeline/scripts/auto-import-watchdog.py 2>&1 | tail -10
echo 'Also triggering Radarr import...'
curl -s -X POST 'http://localhost:7878/api/v3/command?apikey=YOUR_RADARR_API_KEY' -H 'Content-Type: application/json' -d '{"name":"DownloadedMoviesScan","importMode":"move"}' > /dev/null
echo 'Radarr DownloadedMoviesScan triggered.'
curl -s -X POST 'http://localhost:8989/api/v3/command?apikey=YOUR_SONARR_API_KEY' -H 'Content-Type: application/json' -d '{"name":"DownloadedEpisodesScan","importMode":"move"}' > /dev/null
echo 'Sonarr DownloadedEpisodesScan triggered.'

# pipeline-log
#!/bin/bash
echo '=== PIPELINE LOGS (last 3 lines each) ==='
for log in torrent-doctor auto-import auto-dedup balance-8tb anti-dupe discovery-engine nightly-backup protect-20tb; do
    f="/mnt/20TB/homelab/media/Pipeline/logs/$log.log"
    [ -f "$f" ] && echo "--- $log ---" && tail -1 "$f" 2>/dev/null
done
echo ''
echo 'Full logs: /mnt/20TB/homelab/media/Pipeline/logs/'

# pipeline-peers
#!/bin/bash
echo '=== PIPELINE PEERS ==='
python3 -c "
import urllib.request, urllib.parse, json
for label, url in [('OVERFLOW', 'http://127.0.0.1:8083'), ('LAPTOP', 'http://<local-ip>:8080')]:
    try:
        cj = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(cj)
        o.open(urllib.request.Request(f'{url}/api/v2/auth/login', data=urllib.parse.urlencode({'username':'topaz','password':'YOUR_QBIT_PASSWORD'}).encode()), timeout=8)
        ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=15).read())
        t = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/transfer/info'), timeout=8).read())
        prefs = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/app/preferences'), timeout=8).read())
        with_seeds = sum(1 for x in ts if x.get('num_seeds',0)>0)
        total_seeds = sum(x.get('num_seeds',0) for x in ts)
        total_peers = sum(x.get('num_leechs',0) for x in ts)
        active = sum(1 for x in ts if x.get('dlspeed',0)>0)
        dht = t.get('dht_nodes',0)
        conn = t.get('connection_status','?')
        # Get tracker count from first torrent
        tc = 0
        if ts:
            try:
                tr = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/trackers?hash={ts[0]["hash"]}'), timeout=8).read())
                tc = len(tr)
            except: pass
        print(f'{label}: {len(ts)} torrents, {active} active, {with_seeds} w/ seeds')
        print(f'  Total seeds: {total_seeds} | Total peers: {total_peers}')
        print(f'  DHT: {dht} nodes | Status: {conn} | Trackers/torrent: {tc}')
        print(f'  DHT={prefs.get("dht")} PEX={prefs.get("pex")} LSD={prefs.get("lsd")} Enc={prefs.get("encryption")}')
        print()
    except Exception as e: print(f'{label}: {str(e)[:50]}')
"

# pipeline-queue
#!/bin/bash
echo '=== PIPELINE QUEUE ==='
echo 'Sonarr:'
curl -s 'http://localhost:8989/api/v3/queue?apikey=YOUR_SONARR_API_KEY' 2>/dev/null | python3 -c "
import json,sys; d=json.load(sys.stdin); records=d.get('records',[]); print(f'  {len(records)} items')
for r in records[:10]:
    status=r.get('status','?'); title=r.get('title','?')[:55]; size=r.get('size',0)/1e9; left=r.get('sizeleft',0)/1e9
    print(f'  [{status:10s}] {title} ({size:.1f}GB)')
" 2>/dev/null
echo ''
echo 'Radarr:'
curl -s 'http://localhost:7878/api/v3/queue?apikey=YOUR_RADARR_API_KEY' 2>/dev/null | python3 -c "
import json,sys; d=json.load(sys.stdin); records=d.get('records',[]); print(f'  {len(records)} items')
for r in records[:10]:
    status=r.get('status','?'); title=r.get('title','?')[:55]; size=r.get('size',0)/1e9; left=r.get('sizeleft',0)/1e9
    print(f'  [{status:10s}] {title} ({size:.1f}GB)')
" 2>/dev/null

# pipeline-recover
#!/bin/bash
echo '=== PIPELINE RECOVER ==='
echo '1. NFS remount on laptop...'
ssh -o ConnectTimeout=5 laptop 'sudo mount -a 2>/dev/null && echo "  NFS remounted"' 2>/dev/null || echo '  Laptop SSH slow (normal)'
echo '2. Compose validate...'
docker compose -f /mnt/20TB/homelab/media/compose/docker-compose.yml config --quiet 2>&1 && echo '  Compose VALID' || echo '  Compose BROKEN - restore from backup'
echo '3. Restart stuck containers...'
for c in gluetun-overflow qbittorrent-overflow; do
    docker restart $c 2>/dev/null && echo "  Restarted: $c"
done
echo '4. Re-apply MAX mode...'
/usr/local/bin/pipeline max 2>&1 | head -1
echo '5. Re-announce all...'
/usr/local/bin/pipeline-seed 2>&1 | head -3
echo 'Recovery complete.'

# pipeline-restart
#!/bin/bash
# pipeline-restart — Quick restart everything
echo 'Pipeline Restart'
echo '==============='
echo
echo '1. Docker containers...'
cd /mnt/20tbhdd/homelab/media/compose && docker-compose up -d 2>&1 | tail -3
echo
echo '2. Network fix...'
/usr/local/bin/docker-forward.sh
echo
echo '3. Plexbot...'
systemctl restart plexbot.service 2>/dev/null && echo '   Plexbot restarted' || echo '   Plexbot: skipped'
echo
echo '4. Health check...'
sleep 10
for port in 8989 7878 9696 5055 32400; do
  curl -sf --max-time 3 http://localhost:$port >/dev/null 2>&1 && echo "   Port $port: OK" || echo "   Port $port: DOWN"
done
echo
echo 'Done. Pipeline restarted.'

# pipeline-scan
#!/bin/bash
echo '=== PIPELINE SCAN — Refresh Plex Libraries ==='
curl -s -H 'X-Plex-Token: YOUR_PLEX_TOKEN' 'http://localhost:32400/library/sections/3/refresh' > /dev/null && echo 'Movies library scan triggered'
curl -s -H 'X-Plex-Token: YOUR_PLEX_TOKEN' 'http://localhost:32400/library/sections/4/refresh' > /dev/null && echo 'TV Shows library scan triggered'
echo 'Plex will detect new content within 1-2 minutes.'

# pipeline-seed
#!/bin/bash
echo '=== PIPELINE SEED — Max Peer Discovery ==='
python3 -c "
import urllib.request, urllib.parse, json
TRACKERS = ['udp://tracker.opentrackr.org:1337/announce','udp://open.demonii.com:1337/announce','udp://tracker.openbittorrent.com:6969/announce','udp://open.stealth.si:80/announce','udp://tracker.torrent.eu.org:451/announce','udp://explodie.org:6969/announce','udp://tracker.moeking.me:6969/announce','udp://tracker.bitsearch.to:1337/announce','udp://p4p.arenabg.com:1337/announce','udp://movies.zsw.ca:6969/announce','udp://retracker.lanta-net.ru:2710/announce','http://tracker.openbittorrent.com:80/announce','udp://tracker.dler.org:6969/announce','udp://odd-hd.fr:6969/announce','udp://tracker.leech.ie:1337/announce']
for label, url in [('OVERFLOW', 'http://127.0.0.1:8083'), ('LAPTOP', 'http://<local-ip>:8080')]:
    try:
        cj = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(cj)
        o.open(urllib.request.Request(f'{url}/api/v2/auth/login', data=urllib.parse.urlencode({'username':'topaz','password':'YOUR_QBIT_PASSWORD'}).encode()), timeout=8)
        ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=15).read())
        hashes = '|'.join(t['hash'] for t in ts)
        for tr in TRACKERS:
            try: o.open(urllib.request.Request(f'{url}/api/v2/torrents/addTrackers', data=urllib.parse.urlencode({'hashes':hashes,'urls':tr}).encode(), method='POST'), timeout=5)
            except: pass
        o.open(urllib.request.Request(f'{url}/api/v2/torrents/reannounce', data=urllib.parse.urlencode({'hashes':hashes}).encode(), method='POST'), timeout=10)
        # Resume paused
        paused = [t['hash'] for t in ts if t.get('state') in ('pausedDL','pausedUP')]
        if paused:
            o.open(urllib.request.Request(f'{url}/api/v2/torrents/resume', data=urllib.parse.urlencode({'hashes':'|'.join(paused)}).encode(), method='POST'), timeout=10)
        t = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/transfer/info'), timeout=8).read())
        print(f'  {label}: {len(ts)} torrents re-announced, {len(paused)} resumed, DHT={t.get("dht_nodes",0)}')
    except Exception as e: print(f'  {label}: {str(e)[:50]}')
"
echo 'Peers connecting over next few minutes...'

# pipeline-space
#!/bin/bash
echo '=== PIPELINE SPACE ==='
df -h /mnt/20TB /mnt/8TB / /home | grep -v tmpfs
echo ''
echo '20TB top folders:'
du -sh /mnt/20TB/* 2>/dev/null | sort -rh | head -5
echo ''
echo '8TB top folders:'
du -sh /mnt/8TB/* 2>/dev/null | sort -rh | head -5
echo ''
echo 'Root: pacman cache=' && du -sh /var/cache/pacman/pkg 2>/dev/null
echo 'Root: journals=' && du -sh /var/log/journal 2>/dev/null
echo 'Root: coredumps=' && du -sh /var/lib/systemd/coredump 2>/dev/null

# pipeline-stall
#!/bin/bash
echo '=== PIPELINE STALL DIAGNOSTIC ==='
echo ''
# Check each layer
echo 'VPN:'
docker ps --format '{{.Names}} {{.Status}}' | grep gluetun-overflow
echo -n 'qBit overflow: '
curl -s -m3 -o /dev/null -w '%{http_code}' 'http://127.0.0.1:8083/api/v2/app/version' 2>/dev/null && echo ' reachable' || echo ' DOWN'
echo ''
echo 'Radarr:' && curl -s -m3 -o /dev/null -w '%{http_code}' 'http://localhost:7878/api/v3/system/status?apikey=YOUR_RADARR_API_KEY' 2>/dev/null && echo ' reachable' || echo ' DOWN'
echo 'Sonarr:' && curl -s -m3 -o /dev/null -w '%{http_code}' 'http://localhost:8989/api/v3/system/status?apikey=YOUR_SONARR_API_KEY' 2>/dev/null && echo ' reachable' || echo ' DOWN'
echo 'Prowlarr:' && curl -s -m3 -o /dev/null -w '%{http_code}' 'http://localhost:9696/api/v1/system/status?apikey=YOUR_PROWLARR_API_KEY' 2>/dev/null && echo ' reachable' || echo ' DOWN'
echo 'Plex:' && systemctl is-active plexmediaserver
echo ''
echo 'Download states:'
pipeline status 2>&1 | grep -E 'DL=|TOTAL|Speed|active'
echo ''
echo 'Stalled torrents:'
python3 -c "
import urllib.request, urllib.parse, json
for label, url in [('OVERFLOW', 'http://127.0.0.1:8083'), ('LAPTOP', 'http://<local-ip>:8080')]:
    try:
        cj = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(cj)
        o.open(urllib.request.Request(f'{url}/api/v2/auth/login', data=urllib.parse.urlencode({'username':'topaz','password':'YOUR_QBIT_PASSWORD'}).encode()), timeout=5)
        ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=8).read())
        stalled = sum(1 for t in ts if 'stall' in t.get('state','').lower())
        paused = sum(1 for t in ts if 'pause' in t.get('state','').lower())
        checking = sum(1 for t in ts if 'check' in t.get('state','').lower())
        active = sum(1 for t in ts if t.get('dlspeed',0)>0)
        print(f'{label}: {len(ts)} total, {active} active, {stalled} stalled, {paused} paused, {checking} checking')
    except: print(f'{label}: unreachable')
"
echo ''
echo 'VERDICT:'
python3 -c "
import urllib.request, urllib.parse, json
issues = []
for label, url in [('OVERFLOW', 'http://127.0.0.1:8083'), ('LAPTOP', 'http://<local-ip>:8080')]:
    try:
        cj = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(cj)
        o.open(urllib.request.Request(f'{url}/api/v2/auth/login', data=urllib.parse.urlencode({'username':'topaz','password':'YOUR_QBIT_PASSWORD'}).encode()), timeout=5)
        ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=8).read())
        active = sum(1 for t in ts if t.get('dlspeed',0)>0)
        if active == 0: issues.append(f'{label} has 0 active downloads')
    except: issues.append(f'{label} is unreachable')
if issues:
    for i in issues: print(f'  ISSUE: {i}')
    print('  FIX: pipeline-unstall')
else:
    print('  Pipeline FLOWING — no stalls detected')
"

# pipeline-sync
#!/bin/bash
# pipeline-sync — Push sanitized pipeline to GitHub via desktop
DESKTOP="<user>@<local-ip>"
REPO="/home/topaz/pipeline-repo"
TMP="/tmp/pipeline-sync-$$"
mkdir -p "$TMP"/{scripts,discovery,safeguards,systemd}

echo '=== PIPELINE SYNC ==='

# Copy scripts to staging
cp /mnt/20TB/homelab/media/Pipeline/scripts/*.py "$TMP/scripts/" 2>/dev/null
cp /mnt/20TB/homelab/media/Pipeline/scripts/*.sh "$TMP/scripts/" 2>/dev/null
cp /mnt/20TB/homelab/media/Pipeline/discovery/*.py "$TMP/discovery/" 2>/dev/null
cp /mnt/20TB/homelab/media/Pipeline/safeguards/* "$TMP/safeguards/" 2>/dev/null

# Pipeline commands
for f in /usr/local/bin/pipeline /usr/local/bin/pipeline-*; do
    echo "# $(basename $f)" >> "$TMP/systemd/pipeline-commands.sh"
    cat "$f" >> "$TMP/systemd/pipeline-commands.sh"
    echo '' >> "$TMP/systemd/pipeline-commands.sh"
done

# Systemd units
for f in /etc/systemd/system/pipeline*.service /etc/systemd/system/pipeline*.timer          /etc/systemd/system/torrent-doctor.* /etc/systemd/system/auto-import.*          /etc/systemd/system/anti-dupe.* /etc/systemd/system/protect-*.*          /etc/systemd/system/auto-dedup.* /etc/systemd/system/discovery-engine.*          /etc/systemd/system/nightly-backup.* /etc/systemd/system/complete-media.*          /etc/systemd/system/integrity-check.* /etc/systemd/system/container-watchdog.*          /etc/systemd/system/stalled-rescue.*; do
    [ -f "$f" ] && echo "# $(basename $f)" >> "$TMP/systemd/timer-units.conf" && cat "$f" >> "$TMP/systemd/timer-units.conf" && echo '' >> "$TMP/systemd/timer-units.conf"
done

# Sanitize
echo 'Sanitizing...'
find "$TMP" -type f | while read f; do
    sed -i 's|YOUR_SONARR_API_KEY|YOUR_SONARR_API_KEY|g' "$f"
    sed -i 's|YOUR_RADARR_API_KEY|YOUR_RADARR_API_KEY|g' "$f"
    sed -i 's|YOUR_SONARR_API_KEY|YOUR_SONARR_API_KEY|g' "$f"
    sed -i 's|YOUR_PROWLARR_API_KEY|YOUR_PROWLARR_API_KEY|g' "$f"
    sed -i 's|YOUR_PLEX_TOKEN|YOUR_PLEX_TOKEN|g' "$f"
    sed -i 's|YOUR_TMDB_API_KEY|YOUR_TMDB_API_KEY|g' "$f"
    sed -i 's|YOUR_QBIT_PASSWORD|YOUR_QBIT_PASSWORD|g' "$f"
    sed -i 's|10\.0\.0\.[0-9]*|<local-ip>|g' "$f"
    sed -i 's|184\.75\.[0-9]*\.[0-9]*|<vpn-ip>|g' "$f"
    sed -i 's|<user>@|<user>@|g' "$f"
done

# SCP to desktop repo
scp -P 2224 -r "$TMP"/* "$DESKTOP:$REPO/" 2>/dev/null

# Trigger desktop to commit + push
ssh -p 2224 "$DESKTOP" "cd $REPO && git add -A && git commit -m 'sync: $(date '+%Y-%m-%d %H:%M')' && git push" 2>/dev/null

rm -rf "$TMP"
echo 'Synced to GitHub — all sensitive data sanitized.'

# pipeline-taste
#!/bin/bash
echo '=== PIPELINE TASTE — Refresh Profiles ==='
python3 -c "
import json, os, time
taste_dir = '/mnt/20TB/homelab/media/Pipeline/taste'
os.makedirs(taste_dir, exist_ok=True)
# Read current library size
hl = '/mnt/20TB/homelab/media/Pipeline/have-list.txt'
movies = shows = 0
if os.path.exists(hl):
    with open(hl) as f:
        for line in f:
            if 'Movies' in line and '===' in line:
                movies = int(line.split('-')[1].strip().split()[0]) if '-' in line else movies
            if 'TV Shows' in line and '===' in line:
                shows = int(line.split('-')[1].strip().split()[0]) if '-' in line else shows

for user in ['topazconch', 'astrotopaz']:
    p = json.load(open(os.path.join(taste_dir, f'{user}.json')))
    p['stats'] = {'movies_watched': movies, 'shows_watched': shows, 'total_content': movies+shows, 'last_updated': time.strftime('%Y-%m-%d')}
    with open(os.path.join(taste_dir, f'{user}.json'), 'w') as f: json.dump(p, f, indent=2)
    print(f'  {user}: {len(p["genres"])} genres, {len(p["actors"])} actors')
print(f'Library: {movies} movies + {shows} shows = {movies+shows} total')
"
echo 'Taste profiles updated.'

# pipeline-unstall
#!/bin/bash
echo '=== PIPELINE UNSTALL — Emergency Flow Restore ==='
echo ''
echo '[1/5] Restarting all containers...'
docker restart radarr sonarr prowlarr qbittorrent-overflow gluetun-overflow 2>/dev/null
sleep 8
echo '[2/5] Container watchdog check...'
/usr/local/bin/pipeline-recover 2>&1 | head -5
echo '[3/5] Re-applying MAX mode...'
/usr/local/bin/pipeline max 2>&1 | head -1
echo '[4/5] Force re-announce + clean dead...'
/usr/local/bin/pipeline-seed 2>&1 | head -3
/usr/local/bin/pipeline-clean 2>&1 | grep removed
echo '[5/5] Force import + scan...'
/usr/local/bin/pipeline-import 2>&1 | head -3
/usr/local/bin/pipeline-scan 2>&1 | head -2
echo ''
echo 'Pipeline unstall complete. Flow should resume.'

# pipeline-vpn
#!/bin/bash
echo '=== PIPELINE VPN ==='
echo 'Laptop VPN:'
docker logs gluetun-overflow --tail 1 2>/dev/null | grep 'Public IP' || echo '  Not on server — check laptop'
echo 'Overflow VPN:'
echo -n '  IP: ' && curl -s --max-time 5 http://127.0.0.1:8083/api/v2/app/version > /dev/null 2>&1 && echo 'qBit reachable via VPN' || echo 'NOT reachable'
echo '  Container:' && docker ps --format '{{.Names}} {{.Status}}' | grep gluetun-overflow

