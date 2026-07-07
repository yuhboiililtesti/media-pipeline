#!/usr/bin/env python3
# discovery-engine.py — v2.0 Content Discovery Engine
# Multi-source discovery with scoring, queue management, self-learning, scheduled searches
#
# SEED TYPES:  @Actor  @Director  +Franchise  %Genre  $Network  ~SimilarTo
# MODES:       daily  weekly  monthly  yearly (via --mode flag)

import os, re, sys, time, json, urllib.request, urllib.parse
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

# ─── CONFIG ─────────────────────────────────────────────
PIPELINE    = "/mnt/20TB/homelab/media/Pipeline"
PLEXLIST    = f"{PIPELINE}/plexlist.txt"
LOG_FILE    = f"{PIPELINE}/logs/discovery-engine.log"
CANDIDATES  = f"{PIPELINE}/candidates"
TASTE_PROFILE = f"{PIPELINE}/taste_profile.json"

RADARR_URL  = "http://localhost:7878/api/v3"
SONARR_URL  = "http://localhost:8989/api/v3"
RADARR_KEY  = "YOUR_RADARR_API_KEY"
SONARR_KEY  = "YOUR_SONARR_API_KEY"
TMDB_KEY    = os.environ.get("TMDB_KEY", "")
TMDB_URL    = "https://api.themoviedb.org/3"

MOVIE_ROOT  = "/mnt/20TB/Movies 1"
TV_ROOT     = "/mnt/20TB/TV Shows 1"

MODE = sys.argv[1] if len(sys.argv) > 1 else "daily"

# ─── SCORING ────────────────────────────────────────────
SCORES = {
    "manual_request":      100,
    "missing_monitored":    90,
    "franchise":            80,
    "same_director":        70,
    "same_actor":           50,
    "similar_content":      40,
    "genre_match":          35,
    "network_match":        30,
    "trending":             25,
    "highly_rated":         20,
    "taste_match":          15,
    "new_release":          15,
    "upcoming":             10,
}

AUTO_THRESHOLD   = 85  # Score >= 100 → auto-add
REVIEW_THRESHOLD = 50   # Score >= 50  → review queue
# Below 50 → rejected

# ─── LOGGING ─────────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ─── API HELPERS ─────────────────────────────────────────
def tmdb(path, params=None):
    if not TMDB_KEY: return None
    if params is None: params = {}
    params["api_key"] = TMDB_KEY
    url = f"{TMDB_URL}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        log(f"  TMDB: {e}")
        return None

def radarr_get(path):
    try:
        url = f"{RADARR_URL}{path}?apikey={RADARR_KEY}"
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except: return None

def radarr_post(path, data):
    try:
        url = f"{RADARR_URL}{path}?apikey={RADARR_KEY}"
        req = urllib.request.Request(url, data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except: return None

def sonarr_get(path):
    try:
        url = f"{SONARR_URL}{path}?apikey={SONARR_KEY}"
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except: return None

def sonarr_post(path, data):
    try:
        url = f"{SONARR_URL}{path}?apikey={SONARR_KEY}"
        req = urllib.request.Request(url, data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except: return None

# ─── TASTE PROFILE ────────────────────────────────────────
def load_taste_profile():
    """Load learned preferences from taste_profile.json"""
    if os.path.exists(TASTE_PROFILE):
        try:
            return json.load(open(TASTE_PROFILE))
        except: pass
    return {
        "favorite_genres": ["scifi", "thriller", "action"],
        "favorite_directors": [],
        "favorite_actors": [],
        "preferred_decades": ["2000s", "2010s", "2020s"],
        "disliked_genres": [],
        "watched": 0, "deleted": 0, "ignored": 0,
        "genre_scores": {}
    }

def save_taste_profile(profile):
    profile["updated"] = datetime.now().isoformat()
    json.dump(profile, open(TASTE_PROFILE, "w"), indent=2)

def update_taste_from_watched(profile):
    """Analyze watched content to update taste profile"""
    movies = radarr_get("/movie") or []
    genre_counts = defaultdict(int)
    for m in movies:
        if m.get("hasFile"):
            info = radarr_get(f"/movie/{m['id']}")
            if info:
                for g in info.get("genres", []):
                    genre_counts[g.lower()] += 1
    
    sorted_genres = sorted(genre_counts.items(), key=lambda x: -x[1])
    profile["genre_scores"] = dict(sorted_genres)
    profile["favorite_genres"] = [g for g, _ in sorted_genres[:10]]
    save_taste_profile(profile)

# ─── CANDIDATE QUEUE ────────────────────────────────────
def queue_candidate(item, score, reason):
    """Place candidate in auto_add, review, or rejected queue"""
    tmdb_id = item.get("tmdb_id", 0)
    title   = item.get("title", "?")
    year    = item.get("year", "?")
    mtype   = item.get("type", "movie")
    
    entry = f"[{score:3d}] {title} ({year}) [{mtype}] — {reason}  TMDB:{tmdb_id}"
    
    if score >= AUTO_THRESHOLD:
        path = f"{CANDIDATES}/auto_add.txt"
    elif score >= REVIEW_THRESHOLD:
        path = f"{CANDIDATES}/review_queue.txt"
    else:
        path = f"{CANDIDATES}/rejected.txt"
    
    # Check if already queued
    existing = set()
    for q in ["auto_add.txt", "review_queue.txt", "rejected.txt"]:
        qp = f"{CANDIDATES}/{q}"
        if os.path.exists(qp):
            for line in open(qp):
                if str(tmdb_id) in line:
                    existing.add(tmdb_id)
    
    if tmdb_id not in existing:
        with open(path, "a") as f:
            f.write(entry + "\n")
        return path
    return None

def process_auto_add(index):
    """Add auto_add candidates to Radarr/Sonarr"""
    path = f"{CANDIDATES}/auto_add.txt"
    if not os.path.exists(path):
        return 0
    
    lines = [l.strip() for l in open(path) if l.strip()]
    added = 0
    
    for line in lines:
        m = re.search(r'TMDB:(\d+)', line)
        if not m: continue
        tmdb_id = int(m.group(1))
        
        if tmdb_id in index.get("tmdb_movies", set()):
            continue
        
        # Extract title
        title_m = re.match(r'\[\s*\d+\]\s+(.+?)\s+\((\d{4})\)', line)
        title = title_m.group(1) if title_m else "Unknown"
        year = int(title_m.group(2)) if title_m else 0
        
        payload = {
            "tmdbId": tmdb_id, "title": title, "year": year,
            "qualityProfileId": 6, "monitored": True,
            "rootFolderPath": MOVIE_ROOT,
            "addOptions": {"searchForMovie": True}
        }
        result = radarr_post("/movie", payload)
        if result and result.get("id"):
            log(f"  ADDED: {title} ({year})")
            index["tmdb_movies"].add(tmdb_id)
            # Move to downloaded tracking
            with open(f"{CANDIDATES}/downloaded.txt", "a") as f:
                f.write(line + "\n")
            added += 1
            time.sleep(0.3)
    
    # Clear processed
    remaining = [l for l in lines if not any(str(tmdb_id) in l for tmdb_id in index.get("tmdb_movies", set()))]
    # Don't clear — keep queue for reference, just mark processed
    
    return added

# ─── PLEXLIST PARSER ─────────────────────────────────────
def parse_plexlist():
    """Parse plexlist.txt with new seed types"""
    sections = {
        "MOVIES": [], "SHOWS": [],
        "ACTORS": [], "DIRECTORS": [], "FRANCHISES": [],
        "GENRES": [], "NETWORKS": [], "SIMILAR": []
    }
    current = None
    
    for line in open(PLEXLIST):
        line = line.strip()
        if not line: continue
        
        # Skip pure comments
        if line.startswith("#") and not any(line.startswith(f"# {p}") for p in "@+%$~"):
            continue
        
        # Section headers
        m = re.match(r'\[(MOVIES|SHOWS|ACTORS|DIRECTORS|FRANCHISES|GENRES|NETWORKS|SIMILAR)\]', line)
        if m:
            current = m.group(1)
            continue
        
        clean = line.lstrip("# ").strip()
        
        if clean.startswith("@") and current in ("ACTORS", "DIRECTORS"):
            name = clean[1:].strip()
            stype = "actor" if current == "ACTORS" else "director"
            sections[current].append((stype, name))
        elif clean.startswith("+"):
            parts = clean[1:].strip().split()
            if parts and parts[0].isdigit():
                sections["FRANCHISES"].append(int(parts[0]))
            elif parts:
                # Named franchise — search TMDB
                sections["FRANCHISES"].append(clean[1:].strip())
        elif clean.startswith("%"):
            sections["GENRES"].append(clean[1:].strip().lower())
        elif clean.startswith("$"):
            sections["NETWORKS"].append(clean[1:].strip())
        elif clean.startswith("~"):
            sections["SIMILAR"].append(clean[1:].strip())
        elif current in ("MOVIES", "SHOWS") and not line.startswith("#"):
            sections[current].append(clean)
    
    log(f"  Seeds: {len(sections['ACTORS'])} actors, {len(sections['DIRECTORS'])} directors, "
        f"{len(sections['FRANCHISES'])} franchises, {len(sections['GENRES'])} genres, "
        f"{len(sections['NETWORKS'])} networks, {len(sections['SIMILAR'])} similar-to")
    return sections

# ─── INDEX ───────────────────────────────────────────────
def build_index():
    index = {"movies": set(), "shows": set(), "tmdb_movies": set(), "tmdb_all": set()}
    for m in (radarr_get("/movie") or []):
        index["movies"].add(m.get("title", "").lower().strip())
        if m.get("tmdbId"):
            index["tmdb_movies"].add(m["tmdbId"])
            index["tmdb_all"].add(m["tmdbId"])
    for s in (sonarr_get("/series") or []):
        index["shows"].add(s.get("title", "").lower().strip())
    # Load previously rejected
    rp = f"{CANDIDATES}/rejected.txt"
    if os.path.exists(rp):
        for line in open(rp):
            m = re.search(r'TMDB:(\d+)', line)
            if m: index["tmdb_all"].add(int(m.group(1)))
    return index

def search_movie(title, year=None):
    params = {"query": title, "include_adult": "false"}
    if year: params["year"] = year
    data = tmdb("/search/movie", params)
    return data["results"][0] if data and data.get("results") else None

def search_person(name):
    data = tmdb("/search/person", {"query": name})
    if data and data.get("results"):
        p = data["results"][0]
        return p["id"], p["name"]
    return None, None

def search_collection(name):
    data = tmdb("/search/collection", {"query": name})
    if data and data.get("results"):
        return data["results"][0]["id"]
    return None

# ─── SCANNERS ────────────────────────────────────────────
def scan_missing(sections, index, profile):
    """Priority 2: Missing monitored content"""
    log("--- Scanner: Missing Monitored ---")
    added = 0
    movies = radarr_get("/movie") or []
    missing = [m for m in movies if m.get("monitored") and not m.get("hasFile")]
    log(f"  Already monitored missing: {len(missing)} movies (handled by RSS)")
    return added

def scan_franchises(sections, index, profile):
    """Scan franchise collections"""
    log("--- Scanner: Franchises ---")
    added = 0
    for item in sections["FRANCHISES"]:
        coll_id = item if isinstance(item, int) else search_collection(item)
        if not coll_id: continue
        data = tmdb(f"/collection/{coll_id}")
        if not data: continue
        cname = data.get("name", f"Coll {coll_id}")
        log(f"  {cname}")
        for part in data.get("parts", []):
            tid = part.get("id", 0)
            if tid in index["tmdb_all"]: continue
            title = part.get("title", "")
            year = part.get("release_date", "0000")[:4]
            score = SCORES["franchise"]
            queue_candidate({"tmdb_id": tid, "title": title, "year": year, "type": "movie"}, score, f"Franchise: {cname}")
            added += 1
            time.sleep(0.15)
    return added

def scan_actor_director(sections, index, profile):
    """Scan actor and director filmographies"""
    log("--- Scanner: Actors/Directors ---")
    added = 0
    for stype, name in sections["ACTORS"] + sections["DIRECTORS"]:
        pid, pname = search_person(name)
        if not pid:
            log(f"  Not found: {name}")
            continue
        
        conf = SCORES["same_actor"] if stype == "actor" else SCORES["same_director"]
        log(f"  {stype.title()}: {pname}")
        
        credits = tmdb(f"/person/{pid}/movie_credits") or {}
        items = credits.get("cast", []) + credits.get("crew", [])
        
        for c in items:
            if stype == "director" and c.get("job") != "Director": continue
            if stype == "actor" and "character" not in c: continue
            
            tid = c.get("id", 0)
            if tid in index["tmdb_all"]: continue
            
            title = c.get("title", c.get("original_title", ""))
            year = c.get("release_date", "0000")[:4]
            score = conf + (SCORES["taste_match"] if any(g.lower() in str(profile.get("favorite_genres", [])).lower() for g in [title]) else 0)
            queue_candidate({"tmdb_id": tid, "title": title, "year": year, "type": "movie"}, score, f"{stype.title()}: {pname}")
            added += 1
            time.sleep(0.15)
        time.sleep(0.3)
    return added

def scan_similar(sections, index, profile):
    """Scan similar-to seeds"""
    log("--- Scanner: Similar Content ---")
    added = 0
    for title in sections["SIMILAR"][:20]:
        m = re.match(r'^(.+?)\s*(?:\((\d{4})\))?\s*$', title)
        s_title = m.group(1).strip() if m and m.group(1) and len(m.group(1)) > 2 else title
        s_year = m.group(2) if m and m.group(2) else None
        
        result = search_movie(s_title, s_year)
        if not result: continue
        
        recs = tmdb(f"/movie/{result['id']}/recommendations") or {}
        for rec in recs.get("results", [])[:8]:
            tid = rec.get("id", 0)
            if tid in index["tmdb_all"]: continue
            rtitle = rec.get("title", "")
            ryear = rec.get("release_date", "0000")[:4]
            score = SCORES["similar_content"] + SCORES["taste_match"]
            queue_candidate({"tmdb_id": tid, "title": rtitle, "year": ryear, "type": "movie"}, score, f"Similar to: {s_title}")
            added += 1
            time.sleep(0.15)
    return added

def scan_genres(sections, index, profile):
    """Discover by genre"""
    log("--- Scanner: Genres ---")
    added = 0
    for genre in sections["GENRES"][:5]:
        log(f"  Genre: {genre}")
        # Search discover endpoint
        data = tmdb("/discover/movie", {"with_genres": _get_genre_id(genre), 
                   "sort_by": "popularity.desc", "page": 1})
        if not data: continue
        for m in data.get("results", [])[:10]:
            tid = m.get("id", 0)
            if tid in index["tmdb_all"]: continue
            title = m.get("title", "")
            year = m.get("release_date", "0000")[:4]
            rating = m.get("vote_average", 0)
            score = SCORES["genre_match"] + (SCORES["highly_rated"] if rating >= 7.5 else 0)
            queue_candidate({"tmdb_id": tid, "title": title, "year": year, "type": "movie"}, score, f"Genre: {genre}")
            added += 1
            time.sleep(0.15)
    return added

def scan_trending(sections, index, profile):
    """Scan trending/popular content"""
    log("--- Scanner: Trending ---")
    added = 0
    for endpoint in ["/trending/movie/week", "/movie/popular"]:
        data = tmdb(endpoint)
        if not data: continue
        for m in data.get("results", [])[:15]:
            tid = m.get("id", 0)
            if tid in index["tmdb_all"]: continue
            title = m.get("title", "")
            year = m.get("release_date", "0000")[:4]
            rating = m.get("vote_average", 0)
            pop = m.get("popularity", 0)
            score = SCORES["trending"] + (SCORES["highly_rated"] if rating >= 7.5 else 0) + min(int(pop / 50), 10)
            queue_candidate({"tmdb_id": tid, "title": title, "year": year, "type": "movie"}, score, f"Trending ({endpoint})")
            added += 1
            time.sleep(0.15)
    return added

def scan_new_releases(sections, index, profile):
    """Scan upcoming and new releases"""
    log("--- Scanner: New Releases ---")
    added = 0
    
    # Upcoming theatrical
    today = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    
    for endpoint, label in [
        (f"/discover/movie?primary_release_date.gte={today}&primary_release_date.lte={future}", "Upcoming 90d"),
        ("/movie/now_playing", "Now Playing"),
    ]:
        path = endpoint if "?" in endpoint else f"{endpoint}?language=en-US&page=1"
        data = tmdb(path if "?" in endpoint else endpoint, {"language": "en-US", "page": "1"} if "?" not in endpoint else None)
        if not data: continue
        for m in data.get("results", [])[:10]:
            tid = m.get("id", 0)
            if tid in index["tmdb_all"]: continue
            title = m.get("title", "")
            year = m.get("release_date", "0000")[:4]
            score = SCORES["new_release"]
            queue_candidate({"tmdb_id": tid, "title": title, "year": year, "type": "movie"}, score, label)
            added += 1
            time.sleep(0.15)
    return added

# ─── GENRE ID MAPPING ────────────────────────────────────
GENRE_IDS = {}
def _get_genre_id(name):
    if not GENRE_IDS:
        data = tmdb("/genre/movie/list")
        if data:
            for g in data.get("genres", []):
                GENRE_IDS[g["name"].lower()] = g["id"]
    return str(GENRE_IDS.get(name, ""))

# ─── MAIN ────────────────────────────────────────────────
def main():
    mode = MODE
    log("=" * 60)
    log(f"DISCOVERY ENGINE v2.0 — Mode: {mode}")
    log("=" * 60)
    
    if not TMDB_KEY:
        log("No TMDB_KEY — scanners skipped")
    
    sections = parse_plexlist()
    index = build_index()
    profile = load_taste_profile()
    
    # Update taste profile weekly
    if mode in ("weekly", "monthly", "yearly"):
        update_taste_from_watched(profile)
        profile = load_taste_profile()
        log(f"  Taste: {len(profile.get('genre_scores', {}))} genres scored")
    
    total_queued = 0
    
    if TMDB_KEY:
        # Run scanners based on mode
        scanners = [
            ("Missing Monitored", scan_missing, True),
            ("Franchises", scan_franchises, True),
            ("Actors/Directors", scan_actor_director, True),
            ("Similar Content", scan_similar, True),
        ]
        
        # Mode-specific scanners
        if mode in ("daily", "weekly"):
            scanners.append(("Genres", scan_genres, True))
        if mode in ("daily", "weekly"):
            scanners.append(("Trending", scan_trending, True))
        if mode in ("weekly", "monthly"):
            scanners.append(("New Releases", scan_new_releases, True))
        
        for name, func, enabled in scanners:
            if enabled:
                n = func(sections, index, profile)
                total_queued += n
                log(f"  {name}: {n} candidates")
    
    # Process auto_add queue
    log("--- Processing Auto-Add Queue ---")
    added = process_auto_add(index)
    log(f"  Auto-added: {added} to Radarr")
    
    # Stats
    for q in ["auto_add.txt", "review_queue.txt", "rejected.txt"]:
        qp = f"{CANDIDATES}/{q}"
        count = len(open(qp).readlines()) if os.path.exists(qp) else 0
        log(f"  {q}: {count} items")
    
    log(f"TOTAL: {total_queued} candidates, {added} added")
    log("DISCOVERY ENGINE COMPLETE")

if __name__ == "__main__":
    main()
