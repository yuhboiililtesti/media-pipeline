#!/usr/bin/env python3
# complete-media.py — Find and fill ALL gaps in media library
# Missing seasons, missing episodes, franchise gaps, sequels, prequels

import urllib.request, json, time, os

TMDB_KEY = '5e00e3a8059e33e9f559bf884ed726ed'
RADARR_KEY = 'e7746c269b2b43b2a2d102f6dea434e0'
SONARR_KEY = 'YOUR_SONARR_API_KEY'
RADARR_URL = 'http://localhost:7878/api/v3'
SONARR_URL = 'http://localhost:8989/api/v3'

LOG = '/mnt/20TB/homelab/media/Pipeline/logs/complete-media.log'
def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    with open(LOG, 'a') as f: f.write(line + '\n')

log('=' * 60)
log('MEDIA COMPLETION ENGINE - Finding all gaps')
log('Refreshing taste engine...')
try:
    import sys; sys.path.insert(0, '/mnt/20TB/homelab/media/Pipeline')
    from discovery.taste import update_all as taste_update
    taste_update('daily')
    log('Taste updated')
except Exception as e:
    log(f'Taste update skipped: {e}')

total_added = 0

# ─── 1. MISSING TV SEASONS/EPISODES (TOP PRIORITY) ───
log('--- PRIORITY 1 (TOP): Missing Episodes + New Seasons of EXISTING shows only ---')
try:
    r = urllib.request.urlopen(f'{SONARR_URL}/series?apikey={SONARR_KEY}', timeout=30)
    shows = json.loads(r.read())
    
    incomplete = []
    for s in shows:
        if not s.get('monitored'): continue
        stats = s.get('statistics', {})
        total_eps = stats.get('totalEpisodeCount', 0)
        file_eps = stats.get('episodeFileCount', 0)
        missing = total_eps - file_eps
        if missing > 0:
            incomplete.append((missing, s['title'], s['id']))
    
    incomplete.sort(reverse=True)
    log(f'  Shows with missing episodes: {len(incomplete)}')
    
    # Trigger season search for top 30 most-missing
    searched = 0
    for missing, title, sid in incomplete[:30]:
        cmd = {'name': 'SeriesSearch', 'seriesId': sid}
        try:
            req = urllib.request.Request(f'{SONARR_URL}/command?apikey={SONARR_KEY}',
                data=json.dumps(cmd).encode(), headers={'Content-Type': 'application/json'}, method='POST')
            urllib.request.urlopen(req, timeout=10)
            log(f'  Season search: {title} ({missing} missing)')
            searched += 1
            time.sleep(0.3)
        except:
            pass
    
    log(f'  Triggered {searched} season searches')
    
    # Print remaining incomplete shows (not searched this run)
    if len(incomplete) > 30:
        log(f'  Remaining {len(incomplete)-30} shows for next run:')
        for missing, title, _ in incomplete[30:35]:
            log(f'    {title}: {missing} missing')
except Exception as e:
    log(f'  Sonarr error: {e}')

# ─── 2. MISSING MOVIES — BACKLOG SEARCH ───
log('\n--- PRIORITY 2: Missing Monitored Movies (only if already tracked in Radarr) ---')
try:
    r = urllib.request.urlopen(f'{RADARR_URL}/movie?apikey={RADARR_KEY}', timeout=30)
    movies = json.loads(r.read())
    missing = [m for m in movies if m.get('monitored') and not m.get('hasFile')]
    log(f'  Missing movies: {len(missing)}')
    
    # Trigger missing movie search
    cmd = {'name': 'MissingMoviesSearch'}
    req = urllib.request.Request(f'{RADARR_URL}/command?apikey={RADARR_KEY}',
        data=json.dumps(cmd).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    urllib.request.urlopen(req, timeout=10)
    log('  MissingMoviesSearch triggered')
except Exception as e:
    log(f'  Radarr error: {e}')

# ─── 3. FRANCHISE GAPS ───
log('\n--- PRIORITY 3: Franchise/Collection Gaps ---')
COLLECTIONS = {
    10: 'Star Wars', 1241: 'Harry Potter', 528: 'The Dark Knight',
    1570: 'Marvel Cinematic Universe', 86311: 'How to Train Your Dragon',
    8091: 'Alien', 1704: 'Planet of the Apes', 748: 'Pirates of the Caribbean',
    295: 'Back to the Future', 424: 'The Lord of the Rings',
    84: 'Jurassic Park', 873: 'The Hunger Games', 335: 'Mission: Impossible',
    427: 'Fast & Furious', 1271: 'Die Hard', 886: 'Indiana Jones',
    121: 'Toy Story', 10194: 'Kung Fu Panda', 10484: 'How to Train Your Dragon',
}

try:
    # Get existing movies
    existing_tmdb = {m.get('tmdbId') for m in movies if m.get('tmdbId')}
    
    for coll_id, coll_name in COLLECTIONS.items():
        try:
            r = urllib.request.urlopen(f'https://api.themoviedb.org/3/collection/{coll_id}?api_key={TMDB_KEY}', timeout=10)
            data = json.loads(r.read())
            parts = data.get('parts', [])
            
            missing_parts = [p for p in parts if p['id'] not in existing_tmdb]
            if missing_parts:
                log(f'  {coll_name}: {len(missing_parts)}/{len(parts)} missing')
                for p in missing_parts[:5]:
                    title = p['title']
                    year = p.get('release_date', '0000')[:4] or '2020'
                    payload = {'tmdbId': p['id'], 'title': title, 'year': int(year) if year.isdigit() else 2020,
                              'qualityProfileId': 6, 'monitored': True, 'rootFolderPath': '/mnt/20TB/Movies 1',
                              'addOptions': {'searchForMovie': True}}
                    try:
                        req = urllib.request.Request(f'{RADARR_URL}/movie?apikey={RADARR_KEY}',
                            data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, method='POST')
                        urllib.request.urlopen(req, timeout=10)
                        existing_tmdb.add(p['id'])
                        total_added += 1
                    except:
                        pass
                    time.sleep(0.2)
            else:
                log(f'  {coll_name}: COMPLETE ({len(parts)}/{len(parts)})')
            time.sleep(0.3)
        except:
            pass
except Exception as e:
    log(f'  Franchise error: {e}')

# ─── 4. SEQUEL/PREQUEL DETECTION ───
log('\n--- PRIORITY 4: Sequel/Prequel Detection ---')
try:
    # For each owned movie, check TMDB for sequels/prequels via collection membership
    owned = [m for m in movies if m.get('hasFile') and m.get('tmdbId')]
    log(f'  Scanning {len(owned)} owned movies for sequels/prequels...')
    
    found = 0
    for m in owned[:100]:  # Limit to first 100 to avoid rate limiting
        tid = m['tmdbId']
        try:
            r = urllib.request.urlopen(f'https://api.themoviedb.org/3/movie/{tid}?api_key={TMDB_KEY}', timeout=10)
            data = json.loads(r.read())
            coll = data.get('belongs_to_collection')
            if coll:
                coll_id = coll['id']
                coll_name = coll['name']
                r2 = urllib.request.urlopen(f'https://api.themoviedb.org/3/collection/{coll_id}?api_key={TMDB_KEY}', timeout=10)
                coll_data = json.loads(r2.read())
                
                for part in coll_data.get('parts', []):
                    if part['id'] not in existing_tmdb:
                        title = part['title']
                        year = part.get('release_date', '0000')[:4] or '2020'
                        payload = {'tmdbId': part['id'], 'title': title, 'year': int(year) if year.isdigit() else 2020,
                                   'qualityProfileId': 6, 'monitored': True, 'rootFolderPath': '/mnt/20TB/Movies 1',
                                   'addOptions': {'searchForMovie': True}}
                        try:
                            req = urllib.request.Request(f'{RADARR_URL}/movie?apikey={RADARR_KEY}',
                                data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, method='POST')
                            urllib.request.urlopen(req, timeout=10)
                            existing_tmdb.add(part['id'])
                            found += 1
                            total_added += 1
                        except:
                            pass
                        time.sleep(0.15)
            time.sleep(0.2)
        except:
            pass
    log(f'  Added {found} sequels/prequels')
except Exception as e:
    log(f'  Sequel detection error: {e}')

log(f'\nTOTAL ADDED: {total_added}')
log('MEDIA COMPLETION ENGINE DONE')
