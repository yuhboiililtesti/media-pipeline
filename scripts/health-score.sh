#!/usr/bin/env python3
import subprocess, json, urllib.request, os, time

OUTPUT = "/mnt/20TB/homelab/media/Pipeline/state/HEALTH_SCORE.json"
QBIT = "http://<laptop-ip>:8080"
QBIT_USER = "topaz"
QBIT_PASS = "YOUR_QBIT_PASSWORD"

def pct_to_score(pct):
    if pct > 95: return 10
    if pct > 90: return 25
    if pct > 85: return 50
    if pct > 80: return 70
    return 90

def qbit_api(path):
    try:
        # Login
        import urllib.parse
        cookie_jar = urllib.request.HTTPCookieProcessor()
        opener = urllib.request.build_opener(cookie_jar)
        data = urllib.parse.urlencode({"username": QBIT_USER, "password": QBIT_PASS}).encode()
        opener.open(urllib.request.Request(f"{QBIT}/api/v2/auth/login", data=data), timeout=10)
        r = opener.open(urllib.request.Request(f"{QBIT}{path}"), timeout=10)
        return json.loads(r.read())
    except:
        return {}

# Storage
storage = 100
for mp in ["/mnt/20TB", "/mnt/8TB"]:
    stat = os.statvfs(mp)
    pct = ((stat.f_blocks - stat.f_bavail) / stat.f_blocks) * 100
    s = pct_to_score(pct)
    storage = min(storage, s)

# Network
network = 0
if subprocess.run(["ping", "-c1", "-W2", "<laptop-ip>"], capture_output=True).returncode == 0:
    network = 75
if subprocess.run(["ping", "-c1", "-W2", "1.1.1.1"], capture_output=True).returncode == 0:
    network = min(network + 25, 100)

# Downloads
downloads = 0
info = qbit_api("/api/v2/transfer/info")
dht = info.get("dht_nodes", 0)
speed = info.get("dl_info_speed", 0)
torrents = qbit_api("/api/v2/torrents/info?filter=downloading")
active = len(torrents) if isinstance(torrents, list) else 0

if dht > 0 or active > 0:
    downloads = 60
    if dht >= 300: downloads += 15
    elif dht >= 100: downloads += 5
    if speed > 0: downloads += 10
    if active > 0: downloads += 15
    downloads = min(downloads, 100)

# Plex
plex = 0
if subprocess.run(["systemctl", "is-active", "--quiet", "plexmediaserver"]).returncode == 0:
    plex = 70
    try:
        r = urllib.request.urlopen("http://localhost:32400/identity?X-Plex-Token=YOUR_PLEX_TOKEN", timeout=5)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.read())
        if root.get("claimed") == "1": plex += 30
    except: pass

# Pipeline timers
pipeline = 0
result = subprocess.run(["systemctl", "list-timers", "--no-pager"], capture_output=True, text=True)
active_timers = sum(1 for line in result.stdout.split(chr(10)) if any(
    t in line for t in ["torrent-doc", "tdarr-post", "balance", "nightly", "discovery", "seed"]))
pipeline = min(active_timers * 12, 100)

# Overall
overall = (storage + network + downloads + plex + pipeline) // 5

# Disk details
disk20 = int(((os.statvfs("/mnt/20TB").f_blocks - os.statvfs("/mnt/20TB").f_bavail) / os.statvfs("/mnt/20TB").f_blocks) * 100)
disk8 = int(((os.statvfs("/mnt/8TB").f_blocks - os.statvfs("/mnt/8TB").f_bavail) / os.statvfs("/mnt/8TB").f_blocks) * 100)

data = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "overall": overall, "storage": storage, "network": network,
    "downloads": downloads, "plex": plex, "automation": pipeline,
    "details": { "disk_20tb_pct": disk20, "disk_8tb_pct": disk8, "dht_nodes": dht, "active_timers": active_timers }
}
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
json.dump(data, open(OUTPUT, "w"), indent=2)
print(f"Health score: {overall}/100 (storage:{storage} net:{network} dl:{downloads} plex:{plex} auto:{pipeline})")
