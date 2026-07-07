#!/usr/bin/env python3
"""Pipeline-safe dedup — NEVER touches downloads, incomplete, or recently-written files"""

import os, re, time, urllib.request

MEDIA_ROOTS = [
    '/mnt/20TB/Movies 1', '/mnt/20TB/Movies 4', '/mnt/8TB/Movies 2',
    '/mnt/20TB/TV Shows 1', '/mnt/8TB/TV Shows 2'
]
EXCLUDE_PATHS = ['/mnt/20TB/homelab/media/downloads', '/mnt/20TB/homelab/media/encodes', '/mnt/20TB/transcode-temp']
EXT = ('.mkv', '.mp4', '.avi', '.m4v', '.webm')
SAFE_AGE = 600  # 10 min — skip files being written/encoded
LOG = '/mnt/20TB/homelab/media/Pipeline/logs/auto-dedup.log'

freed = 0; deleted = 0; kept = 0; skipped = 0

def log(msg):
    print(msg)
    with open(LOG, 'a') as f: f.write(msg + '\n')

def is_safe(fpath):
    for ex in EXCLUDE_PATHS:
        if fpath.startswith(ex): return False
    if 'incomplete' in fpath.lower(): return False
    try:
        age = time.time() - os.path.getmtime(fpath)
        if age < SAFE_AGE: return False
    except: pass
    return True

def norm(name):
    n = name.lower()
    n = re.sub(r'[._\-]', ' ', n)
    n = re.sub(r'\b(1080p|720p|480p|2160p|4k)\b', '', n)
    n = re.sub(r'\b(bluray|blu-ray|web[-]?(dl|rip)|brrip|hdrip|hdtv|dvdrip)\b', '', n)
    n = re.sub(r'\b(x26[45]|hevc|h\.?26[45]|avc|av1)\b', '', n)
    n = re.sub(r'\b(aac|ac3|ddp?|dts|flac|opus|mp3|eac3|truehd|atmos)\b', '', n)
    n = re.sub(r'\b(10bit|8bit|hdr|dovi|dv|sdr)\b', '', n)
    n = re.sub(r'\b(5\.1|7\.1|2\.0|5 1|7 1|2 0|stereo|surround|dual.audio)\b', '', n)
    n = re.sub(r'\b(yify|yts|rarbg|ettv|eztv|tgx|galaxyrg|bone|sm737|me?gusta|jff|lama|oft|edge2020|ntb|dolores|yawntic)\b', '', n)
    n = re.sub(r'\[.*?\]|\(.*?\)', '', n)
    n = re.sub(r'\b(repack|proper|remastered|extended|unrated|directors.cut|theatrical)\b', '', n)
    n = re.sub(r'\b(complete|season|s\d{2}|e\d{2}|episode)\b', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

log(f'=== SAFE DEDUP {time.strftime("%Y-%m-%d %H:%M")} ===')

groups = {}
for root in MEDIA_ROOTS:
    if not os.path.isdir(root): continue
    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            if not f.lower().endswith(EXT): continue
            fpath = os.path.join(dirpath, f)
            if not is_safe(fpath):
                skipped += 1
                continue
            try:
                sz = os.path.getsize(fpath)
                if sz < 10 * 1048576: continue
            except: continue
            key = norm(f)[:100]
            if key not in groups: groups[key] = []
            groups[key].append((fpath, sz))

dupe_groups = {k: v for k, v in groups.items() if len(v) > 1}
log(f'Groups: {len(groups)} total, {len(dupe_groups)} have dupes, {skipped} files skipped (safe)')

for key, files in sorted(dupe_groups.items()):
    def score(fs):
        fp, _ = fs
        s = 0
        if '/mnt/20TB' in fp: s += 100
        if '/Movies 1' in fp: s += 20
        if '/Movies 4' in fp: s += 10
        if 'season' in fp.lower(): s += 30
        if 'x265' in fp.lower() or 'hevc' in fp.lower(): s += 5
        return s
    files.sort(key=score, reverse=True)
    keep = files[0]; kept += 1
    for fp, sz in files[1:]:
        if is_safe(fp):
            try:
                os.remove(fp)
                freed += sz; deleted += 1
            except: pass

for root in MEDIA_ROOTS:
    if not os.path.isdir(root): continue
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for d in dirnames:
            dpath = os.path.join(dirpath, d)
            try:
                if not os.listdir(dpath): os.rmdir(dpath)
            except: pass

for s in [3, 5]:
    try: urllib.request.urlopen(f'http://localhost:32400/library/sections/{s}/refresh?force=0&X-Plex-Token=YOUR_PLEX_TOKEN', timeout=5)
    except: pass

log(f'Kept: {kept} | Deleted: {deleted} | Freed: {freed/1e9:.1f} GB')
