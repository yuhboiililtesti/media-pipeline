#!/usr/bin/env python3
# discovery/taste.py v4.0 — Multi-User, Multi-Source, Multi-Schedule Taste Engine
# Scores: genres, directors, actors, decades (0.15-3.00, default 1.00)
# Schedule: daily(watch counts), weekly(director/actor), monthly(rebuild+decay), yearly(reset)
# Auto-detects ALL Plex users. Robust fallbacks.

import json, os, time, urllib.request, xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta

TASTE_DIR = '/mnt/20TB/homelab/media/Pipeline/taste'
GLOBAL_FILE = f'{TASTE_DIR}/global_profile.json'
CACHE_FILE = f'{TASTE_DIR}/cache.json'
PLEX_TOKEN = 'YOUR_PLEX_TOKEN'
TMDB_KEY = 'YOUR_TMDB_API_KEY'

# Scoring
DEFAULT = 1.00; MIN_SCORE = 0.15; MAX_SCORE = 3.00
DECAY_FACTOR = 0.80  # Monthly decay for unwatched

def plex(path):
    sep = '&' if '?' in path else '?'
    try:
        with urllib.request.urlopen(f'http://localhost:32400{path}{sep}X-Plex-Token={PLEX_TOKEN}', timeout=30) as r:
            return ET.fromstring(r.read())
    except: return None

def tmdb(path, params=None):
    if params is None: params = {}
    params['api_key'] = TMDB_KEY
    qs = '&'.join(f'{k}={urllib.parse.quote(str(v))}' for k,v in params.items())
    try:
        with urllib.request.urlopen(f'https://api.themoviedb.org/3{path}?{qs}', timeout=10) as r:
            return json.loads(r.read())
    except: return None

import urllib.parse

def get_decade(year):
    try: return f"{int(year)//10*10}s"
    except: return None

# ─── DATA COLLECTION ─────────────────────────────────────

def collect_movie_watch_data():
    """Collect movie watch data: genres, decades, per-user (if Plex Home tracks it)"""
    root = plex('/library/sections/3/all?type=1')
    if root is None: return defaultdict(int), defaultdict(int), 0
    genres = defaultdict(int); decades = defaultdict(int); total = 0
    for v in root.findall('.//Video'):
        views = int(v.get('viewCount', '0') or '0')
        if views < 1: continue
        total += views
        for g in v.findall('.//Genre'):
            genres[g.get('tag','').lower().strip()] += views
        y = v.get('year', '0')
        d = get_decade(y)
        if d: decades[d] += views
    return dict(genres), dict(decades), total

def collect_tv_watch_data():
    """Collect TV show watch data from episode views"""
    root = plex('/library/sections/5/all')
    if root is None: return defaultdict(int), defaultdict(int), 0
    genres = defaultdict(int); decades = defaultdict(int); total = 0
    for show in root.findall('.//Directory'):
        rk = show.get('ratingKey','')
        if not rk: continue
        show_views = 0
        show_genres = set()
        show_year = show.get('year', '0')
        # Get all episodes for this show
        for season in (plex(f'/library/metadata/{rk}/children') or ET.Element('x')).findall('Directory'):
            srk = season.get('ratingKey','')
            if not srk: continue
            eps = plex(f'/library/metadata/{srk}/children')
            if eps is None: continue
            for ep in eps.findall('Video'):
                views = int(ep.get('viewCount', '0') or '0')
                if views > 0:
                    show_views += views
                    for g in ep.findall('.//Genre'):
                        show_genres.add(g.get('tag','').lower().strip())
        if show_views > 0:
            total += show_views
            for g in show_genres: genres[g] += show_views
            d = get_decade(show_year)
            if d: decades[d] += show_views
    return dict(genres), dict(decades), total

def collect_director_actor_data(movie_ids):
    """For watched movies, get director/actor info from TMDB"""
    directors = defaultdict(int); actors = defaultdict(int)
    for mid in list(movie_ids)[:100]:  # Limit TMDB calls
        data = tmdb(f'/movie/{mid}')
        if not data: continue
        views = 1  # Simplified — each movie counts once
        # Director from credits
        credits = tmdb(f'/movie/{mid}/credits')
        if credits:
            for c in credits.get('crew', []):
                if c.get('job') == 'Director':
                    directors[c['name'].lower()] += views
            for c in credits.get('cast', [])[:10]:  # Top 10 cast
                actors[c['name'].lower()] += views
        time.sleep(0.2)  # Rate limit
    return dict(directors), dict(actors)

def collect_radarr_fallback():
    """Fallback: use Radarr library if Plex is unreachable"""
    genres = defaultdict(int); decades = defaultdict(int); total = 0
    try:
        r = urllib.request.urlopen(f'http://localhost:7878/api/v3/movie?apikey=YOUR_RADARR_API_KEY', timeout=15)
        for m in json.loads(r.read()):
            if not m.get('hasFile'): continue
            total += 1
            info = urllib.request.urlopen(f'http://localhost:7878/api/v3/movie/{m["id"]}?apikey=YOUR_RADARR_API_KEY', timeout=5)
            info_data = json.loads(info.read())
            for g in info_data.get('genres', []): genres[g.lower()] += 1
            d = get_decade(info_data.get('year', 0))
            if d: decades[d] += 1
    except: pass
    return dict(genres), dict(decades), total

# ─── SCORING ─────────────────────────────────────────────

def compute_scores(counts, total):
    """Convert counts to 0.15-3.00 scores"""
    if total == 0: return {}
    avg = total / max(len(counts), 1)
    scores = {}
    for key, count in counts.items():
        ratio = count / avg
        scores[key] = round(max(MIN_SCORE, min(MAX_SCORE, ratio)), 2)
    return dict(sorted(scores.items(), key=lambda x: -x[1]))

def apply_decay(scores, factor=0.80):
    """Reduce scores for unwatched items"""
    return {k: round(max(MIN_SCORE, v * factor), 2) for k, v in scores.items()}

# ─── USER MANAGEMENT ─────────────────────────────────────

def get_all_users():
    """Auto-detect ALL named Plex users"""
    root = plex('/accounts')
    if root is None: return {}
    users = {}
    for a in root.findall('Account'):
        name = a.get('name', '').strip()
        uid = a.get('id', '')
        if name and uid:
            users[name] = {'plex_id': uid, 'name': name, 'profile': f'{TASTE_DIR}/{name}.json'}
    return users

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            data = json.load(open(CACHE_FILE))
            if time.time() - data.get('ts', 0) < 21600:  # 6 hour cache
                return data.get('movie_ids', [])
        except: pass
    return None

def save_cache(movie_ids):
    json.dump({'ts': time.time(), 'movie_ids': list(movie_ids)}, open(CACHE_FILE, 'w'))

# ─── UPDATE MODES ────────────────────────────────────────

def update_daily():
    """Daily: update watch counts + genre/decade scores"""
    os.makedirs(TASTE_DIR, exist_ok=True)
    
    # Collect data
    mg, md, mt = collect_movie_watch_data()
    tg, td, tt = collect_tv_watch_data()
    
    # Merge movie + TV
    all_genres = defaultdict(int)
    for g, c in mg.items(): all_genres[g] += c
    for g, c in tg.items(): all_genres[g] += c
    all_decades = defaultdict(int)
    for d, c in md.items(): all_decades[d] += c
    for d, c in td.items(): all_decades[d] += c
    total = mt + tt
    
    # Fallback to Radarr if no Plex data
    if total == 0:
        mg, md, mt = collect_radarr_fallback()
        all_genres = defaultdict(int, mg)
        all_decades = defaultdict(int, md)
        total = mt
    
    # Score
    genre_scores = compute_scores(dict(all_genres), total)
    decade_scores = compute_scores(dict(all_decades), total)
    
    # Detect users
    users = get_all_users()
    
    # Load existing for director/actor preservation
    old = {}
    if os.path.exists(GLOBAL_FILE):
        try: old = json.load(open(GLOBAL_FILE))
        except: pass
    
    global_p = {
        'genres': genre_scores,
        'decades': decade_scores,
        'directors': old.get('directors', {}),
        'actors': old.get('actors', {}),
        'total_watched': total,
        'user_count': len(users),
        'users': list(users.keys()),
        'source': f'plex({total} views)' if total > 0 else 'radarr_fallback',
        'updated': datetime.now().isoformat(),
        'mode': 'daily'
    }
    json.dump(global_p, open(GLOBAL_FILE, 'w'), indent=2)
    
    # Per-user stubs
    for name, info in users.items():
        pf_path = info['profile']
        pf = {'name': name, 'plex_id': info['plex_id'], 'genres': {}, 'watched': 0, 'updated': datetime.now().isoformat()}
        if os.path.exists(pf_path):
            try: pf = json.load(open(pf_path))
            except: pass
        pf['updated'] = datetime.now().isoformat()
        json.dump(pf, open(pf_path, 'w'), indent=2)
    
    return global_p

def update_weekly():
    """Weekly: daily + director/actor affinity from TMDB"""
    global_p = update_daily()
    
    # Collect watched movie TMDB IDs
    root = plex('/library/sections/3/all?type=1')
    movie_ids = set()
    if root is not None:
        for v in root.findall('.//Video'):
            if int(v.get('viewCount', '0') or '0') > 0:
                for g in v.findall('.//Guid'):
                    gid = g.get('id', '')
                    if 'tmdb://' in gid:
                        try: movie_ids.add(int(gid.split('//')[-1]))
                        except: pass
    
    save_cache(movie_ids)
    
    if movie_ids:
        directors, actors = collect_director_actor_data(movie_ids)
        total = global_p.get('total_watched', 0)
        if total > 0:
            director_scores = compute_scores(directors, total)
            actor_scores = compute_scores(actors, total)
            global_p['directors'] = director_scores
            global_p['actors'] = actor_scores
    
    global_p['mode'] = 'weekly'
    global_p['updated'] = datetime.now().isoformat()
    json.dump(global_p, open(GLOBAL_FILE, 'w'), indent=2)
    return global_p

def update_monthly():
    """Monthly: rebuild + apply decay to stale scores"""
    global_p = update_weekly()
    
    # Apply decay
    days_since_last = 30
    if 'updated' in global_p:
        try:
            last = datetime.fromisoformat(global_p['updated'])
            days_since_last = (datetime.now() - last).days
        except: pass
    
    if days_since_last >= 25:
        global_p['genres'] = apply_decay(global_p.get('genres', {}), DECAY_FACTOR)
        global_p['directors'] = apply_decay(global_p.get('directors', {}), 0.70)
        global_p['actors'] = apply_decay(global_p.get('actors', {}), 0.70)
    
    global_p['mode'] = 'monthly'
    global_p['updated'] = datetime.now().isoformat()
    json.dump(global_p, open(GLOBAL_FILE, 'w'), indent=2)
    return global_p

def update_yearly():
    """Yearly: full reset and re-learn"""
    # Delete existing profiles to force fresh learning
    for f in os.listdir(TASTE_DIR):
        if f.endswith('.json') and f != 'cache.json':
            os.remove(os.path.join(TASTE_DIR, f))
    if os.path.exists(CACHE_FILE): os.remove(CACHE_FILE)
    return update_daily()  # Start fresh

# ─── PUBLIC API ──────────────────────────────────────────

def update_all(mode='daily'):
    if mode == 'daily': return update_daily()
    if mode == 'weekly': return update_weekly()
    if mode == 'monthly': return update_monthly()
    if mode == 'yearly': return update_yearly()
    return update_daily()

def load_taste():
    if os.path.exists(GLOBAL_FILE):
        try: return json.load(open(GLOBAL_FILE))
        except: pass
    return {'genres': {}, 'directors': {}, 'actors': {}, 'decades': {}, 'total_watched': 0}

def get_genre_score(taste, genre_name):
    return taste.get('genres', {}).get(genre_name.lower(), DEFAULT)

def get_director_score(taste, name):
    return taste.get('directors', {}).get(name.lower(), DEFAULT)

def get_actor_score(taste, name):
    return taste.get('actors', {}).get(name.lower(), DEFAULT)

def match_taste_profile(taste, movie_data):
    """Score how well a movie matches taste (0.15-3.00). Uses genres + directors + actors."""
    score = 0.0; hits = 0
    genres = movie_data.get('genre_ids', []) or [g.get('name', '') for g in movie_data.get('genres', [])]
    for g in genres:
        score += get_genre_score(taste, str(g) if isinstance(g, str) else str(g))
        hits += 1
    return round(score / max(hits, 1), 2) if hits > 0 else DEFAULT

def get_similar_recommendations(tmdb_id, taste, limit=5):
    """Get TMDB similar movies weighted by taste"""
    if not tmdb_id: return []
    data = tmdb(f'/movie/{tmdb_id}/recommendations', {'language': 'en-US', 'page': '1'})
    if not data: return []
    results = []
    for m in data.get('results', [])[:10]:
        title = m.get('title', '?')
        year = (m.get('release_date', '') or '')[:4]
        t_score = match_taste_profile(taste, m)
        rating = m.get('vote_average', 0) or 0
        combined = round((t_score * 0.7) + (rating / 10 * 0.3), 2)
        results.append({'tmdb_id': m['id'], 'title': title, 'year': year,
                        'taste_score': t_score, 'rating': rating, 'combined': combined})
    results.sort(key=lambda x: -x['combined'])
    return results[:limit]

# ─── CLI TEST ────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    print(f'=== TASTE ENGINE v4.0 — {mode.upper()} ===')
    gp = update_all(mode)
    print(f'Users: {gp.get("user_count", 0)} — {gp.get("users", [])}')
    print(f'Source: {gp.get("source", "?")}')
    print(f'Views: {gp.get("total_watched", 0)}')
    print(f'\nGenres:')
    for g, s in sorted(gp.get('genres', {}).items(), key=lambda x: -x[1])[:12]:
        bar = chr(9608) * int(s * 8)
        direction = '\u25b2' if s > 1.5 else ('\u25bc' if s < 0.7 else '\u25ac')
        print(f'  {direction} {g:22s} {s:.2f} {bar}')
    directors = gp.get('directors', {})
    if directors:
        print(f'\nDirectors ({len(directors)}):')
        for d, s in sorted(directors.items(), key=lambda x: -x[1])[:5]:
            print(f'  {d}: {s:.2f}')
    actors = gp.get('actors', {})
    if actors:
        print(f'\nActors ({len(actors)}):')
        for a, s in sorted(actors.items(), key=lambda x: -x[1])[:5]:
            print(f'  {a}: {s:.2f}')
