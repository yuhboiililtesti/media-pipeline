#!/usr/bin/env python3
"""Auto-import watchdog v2: monitors qBits, validates files, triggers Radarr/Sonarr import."""

import urllib.request, urllib.parse, json, time, os, subprocess

QBITS = [
    ('overflow', 'http://localhost:8083'),
    ('laptop', 'http://10.0.0.234:8080'),
]
USER = 'topaz'
PASS = 'YOUR_QBIT_PASSWORD'
LOG = '/mnt/20TB/homelab/media/Pipeline/logs/auto-import.log'

def log(msg):
    t = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{t}] {msg}'
    print(line)
    try:
        with open(LOG, 'a') as f:
            f.write(line + '\n')
    except: pass

def validate_file(filepath):
    """Check if media file is complete and playable. Returns True if valid."""
    if not os.path.exists(filepath):
        return False
    
    # Check file size > 10MB (not a sample)
    if os.path.getsize(filepath) < 10 * 1048576:
        return False
    
    # Check file isn't still being written (mtime > 2 min ago)
    if time.time() - os.path.getmtime(filepath) < 120:
        return False
    
    # ffprobe integrity check
    try:
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
            capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            return True
        log(f'  Validation failed for {os.path.basename(filepath)}: {r.stderr[:100]}')
        return False
    except Exception as e:
        log(f'  Validation error: {e}')
        return False

def find_media_files(directory):
    """Find all media files in a torrent directory."""
    if not os.path.isdir(directory):
        return []
    files = []
    for f in os.listdir(directory):
        fp = os.path.join(directory, f)
        if os.path.isfile(fp) and f.endswith(('.mkv','.mp4','.avi','.m4v')):
            files.append(fp)
    return files

def qbit_auth(url):
    c = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(c)
    o.open(urllib.request.Request(f'{url}/api/v2/auth/login',
        data=urllib.parse.urlencode({'username':USER,'password':PASS}).encode()), timeout=8)
    return o

def trigger_import():
    for name, api_url, api_key in [
        ('Radarr', 'http://localhost:7878', 'YOUR_RADARR_API_KEY'),
        ('Sonarr', 'http://localhost:8989', 'YOUR_SONARR_API_KEY'),
    ]:
        try:
            cmd = 'DownloadedMoviesScan' if 'Radarr' in name else 'DownloadedEpisodesScan'
            urllib.request.urlopen(urllib.request.Request(
                f'{api_url}/api/v3/command?apikey={api_key}',
                data=json.dumps({'name': cmd}).encode(),
                headers={'Content-Type': 'application/json'}, method='POST'), timeout=8)
        except: pass

def main():
    total = 0
    dl_path = '/mnt/20TB/homelab/media/downloads'
    
    for label, url in QBITS:
        try:
            o = qbit_auth(url)
            ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=8).read())
            comp = [t for t in ts if t.get('progress', 0) >= 1.0]
            
            for t in comp:
                name = t['name']
                thash = t['hash']
                src_dir = os.path.join(dl_path, name)
                
                if not os.path.exists(src_dir):
                    # Already imported - remove from qBit
                    try:
                        o.open(urllib.request.Request(f'{url}/api/v2/torrents/delete',
                            data=urllib.parse.urlencode({'hashes':thash,'deleteFiles':'false'}).encode(),
                            method='POST'), timeout=5)
                        log(f'{label}: removed {name[:45]} (already imported)')
                    except: pass
                    continue
                
                # Validate files before import
                media_files = find_media_files(src_dir)
                if not media_files:
                    log(f'{label}: WARNING - no media files in {name[:45]}')
                    continue
                
                all_valid = True
                for mf in media_files:
                    if not validate_file(mf):
                        all_valid = False
                        log(f'{label}: CORRUPTED - {os.path.basename(mf)[:45]} - deleting torrent')
                        # Delete the torrent and files - Radarr will re-download
                        try:
                            o.open(urllib.request.Request(f'{url}/api/v2/torrents/delete',
                                data=urllib.parse.urlencode({'hashes':thash,'deleteFiles':'true'}).encode(),
                                method='POST'), timeout=5)
                        except: pass
                        # Also delete the directory
                        import shutil
                        shutil.rmtree(src_dir, ignore_errors=True)
                        break
                
                if not all_valid:
                    continue
                
                # All files valid — ready to import
                log(f'{label}: validated {name[:45]} — triggering import')
                try:
                    o.open(urllib.request.Request(f'{url}/api/v2/torrents/delete',
                        data=urllib.parse.urlencode({'hashes':thash,'deleteFiles':'false'}).encode(),
                        method='POST'), timeout=5)
                except: pass
                total += 1
                time.sleep(0.5)
            
            if comp:
                trigger_import()
                
        except Exception as e:
            err = str(e)[:80]
            if 'timeout' not in err.lower() and 'refused' not in err.lower():
                log(f'{label}: error - {err}')
    
    if total > 0:
        log(f'Imported {total} completed torrents')
        try:
            urllib.request.urlopen('http://localhost:32400/library/sections/3/refresh?X-Plex-Token=YOUR_PLEX_TOKEN', timeout=5)
        except: pass

if __name__ == '__main__':
    main()
