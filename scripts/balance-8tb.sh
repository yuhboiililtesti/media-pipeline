#!/usr/bin/env python3
# balance-8tb.py — Robust NTFS-aware disk balancer
# Moves oldest media from 8TB to 20TB when >85%, updates Radarr/Sonarr

import os, shutil, json, urllib.request, time, stat

LOG = '/mnt/20TB/homelab/media/Pipeline/logs/balance-8tb.log'
SRC_M = '/mnt/8TB/Movies 2';  DST_M = '/mnt/20TB/Movies 1'
SRC_T = '/mnt/8TB/TV Shows 2'; DST_T = '/mnt/20TB/TV Shows 1'
THRESHOLD = 85; MAX_MOVES = 3
RADARR_KEY = 'YOUR_RADARR_API_KEY'
SONARR_KEY = 'YOUR_SONARR_API_KEY'

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'{ts} {msg}'
    print(line)
    with open(LOG, 'a') as f: f.write(line + '\n')

def get_usage():
    s = os.statvfs('/mnt/8TB')
    return ((s.f_blocks - s.f_bavail) / s.f_blocks) * 100

def get_oldest(src_dir):
    folders = []
    if not os.path.isdir(src_dir): return folders
    for name in os.listdir(src_dir):
        path = os.path.join(src_dir, name)
        if os.path.isdir(path):
            try: folders.append((os.stat(path).st_mtime, path, name))
            except: pass
    folders.sort()
    return folders

def update_radarr(name, dst):
    try:
        r = urllib.request.urlopen(f'http://localhost:7878/api/v3/movie?apikey={RADARR_KEY}', timeout=15)
        for m in json.loads(r.read()):
            p = m.get('path', '') or m.get('folderName', '')
            if name in p or name.lower() in p.lower():
                mid = m['id']
                data = json.dumps({'movieIds': [mid], 'rootFolderPath': dst + '/', 'moveFiles': False}).encode()
                req = urllib.request.Request(f'http://localhost:7878/api/v3/movie/editor?apikey={RADARR_KEY}', data=data, headers={'Content-Type': 'application/json'}, method='PUT')
                urllib.request.urlopen(req, timeout=10)
                return True
    except: pass
    return False

def update_sonarr(name, dst):
    try:
        r = urllib.request.urlopen(f'http://localhost:8989/api/v3/series?apikey={SONARR_KEY}', timeout=15)
        for s in json.loads(r.read()):
            p = s.get('path', '')
            if name in p or name.lower() in p.lower():
                sid = s['id']
                data = json.dumps({'seriesIds': [sid], 'rootFolderPath': dst + '/', 'moveFiles': False}).encode()
                req = urllib.request.Request(f'http://localhost:8989/api/v3/series/editor?apikey={SONARR_KEY}', data=data, headers={'Content-Type': 'application/json'}, method='PUT')
                urllib.request.urlopen(req, timeout=10)
                return True
    except: pass
    return False

def move_folder(src, dst, is_tv=False):
    name = os.path.basename(src)
    dst_path = os.path.join(dst, name)
    
    try:
        # Use shutil.move for cross-filesystem moves
        shutil.move(src, dst_path)
        time.sleep(1)
        
        if is_tv:
            update_sonarr(name, dst)
        else:
            update_radarr(name, dst)
        
        log(f'  MOVED: {name}')
        return True
    except Exception as e:
        log(f'  FAILED {name}: {e}')
        return False

# Main
usage = get_usage()
if usage < THRESHOLD:
    log(f'8TB at {usage:.0f}% — below threshold')
    exit(0)

log(f'8TB at {usage:.0f}% — balancing (max {MAX_MOVES} moves)')
moved = 0

# Movies
for mtime, path, name in get_oldest(SRC_M):
    if moved >= MAX_MOVES: break
    if get_usage() < 80: break
    if move_folder(path, DST_M): moved += 1

# TV
for mtime, path, name in get_oldest(SRC_T):
    if moved >= MAX_MOVES: break
    if get_usage() < 80: break
    if move_folder(path, DST_T, is_tv=True): moved += 1

new_usage = get_usage()
log(f'Done — moved {moved} items. 8TB now {new_usage:.0f}%')
