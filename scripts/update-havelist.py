#!/usr/bin/env python3
"""Auto-update have-list.txt from Plex API — runs after imports"""
import urllib.request, xml.etree.ElementTree as ET, os, time

TOKEN = 'YOUR_PLEX_TOKEN'
HAVELIST = '/tmp/have-list.txt'
DESKTOP = '/home/topaz/home/Pipeline-Doc/have-list.txt'

out = []
out.append('# HAVE-LIST — Complete Media Inventory')
out.append(f'# Auto-updated: {time.strftime("%Y-%m-%d %H:%M")}')
out.append('# If everything is lost, this file tells you what to re-add.')
out.append('')

# Movies
try:
    r = urllib.request.urlopen(f'http://localhost:32400/library/sections/3/all?type=1&X-Plex-Token={TOKEN}', timeout=60)
    root = ET.fromstring(r.read())
    movies = [f'{v.get("title","?")} ({v.get("year","0")})' for v in root.findall('.//Video')]
    out.append(f'=== MOVIES ({len(movies)}) ===')
    for m in sorted(movies): out.append(m)
    out.append('')
except Exception as e:
    out.append(f'=== MOVIES (ERROR: {e}) ===')
    out.append('')

# TV Shows
try:
    r2 = urllib.request.urlopen(f'http://localhost:32400/library/sections/5/all?X-Plex-Token={TOKEN}', timeout=60)
    root2 = ET.fromstring(r2.read())
    shows = []
    for s in root2.findall('.//Directory'):
        title = s.get('title', '?')
        key = s.get('ratingKey', '')
        seasons = 0; eps = 0
        try:
            r3 = urllib.request.urlopen(f'http://localhost:32400/library/metadata/{key}/children?X-Plex-Token={TOKEN}', timeout=10)
            root3 = ET.fromstring(r3.read())
            seasons = len(root3.findall('Directory'))
            for sd in root3.findall('Directory'):
                srk = sd.get('ratingKey', '')
                if srk:
                    try:
                        r4 = urllib.request.urlopen(f'http://localhost:32400/library/metadata/{srk}/children?X-Plex-Token={TOKEN}', timeout=10)
                        eps += len(ET.fromstring(r4.read()).findall('Video'))
                    except: pass
        except: pass
        shows.append(f'{title} — {seasons} seasons, {eps} episodes')
    out.append(f'=== TV SHOWS ({len(shows)}) ===')
    for s in sorted(shows): out.append(s)
    out.append('')
except Exception as e:
    out.append(f'=== TV SHOWS (ERROR: {e}) ===')
    out.append('')

out.append(f'=== TOTALS ===')
out.append(f'Movies: {len(movies)}')
out.append(f'TV Shows: {len(shows)}')

# Write to server
with open(HAVELIST, 'w') as f:
    f.write(chr(10).join(out))

# Copy to desktop
try:
    import subprocess
    subprocess.run(['scp', '-P', '22', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=5',
                    '/tmp/havelist.txt', '<user>@<local-ip>:/home/topaz/home/Pipeline-Doc/have-list.txt'],
                      timeout=30, capture_output=True)
except:
    pass
