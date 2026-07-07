#!/usr/bin/env python3
# discovery/engine.py — v3.0 Autonomous Discovery Orchestrator
# Priority-based request layer: manual → missing → seeds → gaps → related → trending → taste
# With confidence scoring, taste engine, safeguards, 4-queue system, storage/health awareness

import sys, os, re, time, json, urllib.request, urllib.parse
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

# Add parent to path
sys.path.insert(0, "/mnt/20TB/homelab/media/Pipeline")

# ─── CONFIG ────────────────────────────────────────────
PIPELINE    = "/mnt/20TB/homelab/media/Pipeline"
PLEXLIST    = f"{PIPELINE}/plexlist.txt"
LOG_FILE    = f"{PIPELINE}/logs/discovery-engine.log"
CANDIDATES  = f"{PIPELINE}/candidates"

RADARR_URL  = "http://localhost:7878/api/v3"
SONARR_URL  = "http://localhost:8989/api/v3"
RADARR_KEY  = "e7746c269b2b43b2a2d102f6dea434e0"
SONARR_KEY  = "YOUR_SONARR_API_KEY"
TMDB_KEY    = os.environ.get("TMDB_KEY", "")
TMDB_URL    = "https://api.themoviedb.org/3"

MODE = sys.argv[1] if len(sys.argv) > 1 else "daily"

# ─── LOGGING ────────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f: f.write(line + "\n")

# ─── API HELPERS ────────────────────────────────────────
def tmdb(path, params=None):
    if not TMDB_KEY: return None
    if params is None: params = {}
    params["api_key"] = TMDB_KEY
    url = f"{TMDB_URL}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except: return None

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

# ─── IMPORTS ────────────────────────────────────────────
from discovery.taste import update_all, load_taste, get_genre_score, match_taste_profile
from discovery.scoring import *
from safeguards.guard import *

# ─── PARSER ─────────────────────────────────────────────
def parse_plexlist():
    sections = {"MOVIES": [], "SHOWS": [], "ACTORS": [], "DIRECTORS": [],
                "FRANCHISES": [], "GENRES": [], "NETWORKS": [], "SIMILAR": []}
    current = None
    for line in open(PLEXLIST):
        line = line.strip()
        if not line: continue
        if line.startswith("#") and not any(line.startswith(f"# {p}") for p in "@+%$~"):
            continue
        m = re.match(r'\[(MOVIES|SHOWS|ACTORS|DIRECTORS|FRANCHISES|GENRES|NETWORKS|SIMILAR)\]', line)
        if m: current = m.group(1); continue
        clean = line.lstrip("# ").strip()
        if clean.startswith("@") and current in ("ACTORS", "DIRECTORS"):
            sections[current].append((current.lower()=="actors" and "actor" or "director", clean[1:].strip()))
        elif clean.startswith("+"): 
            parts = clean[1:].strip().split()
            sections["FRANCHISES"].append(int(parts[0]) if parts and parts[0].isdigit() else clean[1:].strip())
        elif clean.startswith("%"): sections["GENRES"].append(clean[1:].strip().lower())
        elif clean.startswith("$"): sections["NETWORKS"].append(clean[1:].strip())
        elif clean.startswith("~"): sections["SIMILAR"].append(clean[1:].strip())
        elif current in ("MOVIES", "SHOWS") and not line.startswith("#"):
            sections[current].append(clean)
    return sections

def build_index():
    idx = {"movies": set(), "shows": set(), "tmdb_movies": set(), "tmdb_all": set()}
    for m in (radarr_get("/movie") or []):
        idx["movies"].add(m.get("title","").lower().strip())
        if m.get("tmdbId"): idx["tmdb_movies"].add(m["tmdbId"]); idx["tmdb_all"].add(m["tmdbId"])
    for s in (sonarr_get("/series") or []):
        idx["shows"].add(s.get("title","").lower().strip())
    for q in ["rejected.txt","quarantine.txt"]:
        qp = f"{CANDIDATES}/{q}"
        if os.path.exists(qp):
            for l in open(qp):
                m = re.search(r'TMDB:(\d+)', l)
                if m: idx["tmdb_all"].add(int(m.group(1)))
    return idx

def search_movie(title, year=None):
    params = {"query": title, "include_adult": "false"}
    if year: params["year"] = year
    data = tmdb("/search/movie", params)
    return data["results"][0] if data and data.get("results") else None

def search_person(name):
    data = tmdb("/search/person", {"query": name})
    if data and data.get("results"):
        return data["results"][0]["id"], data["results"][0]["name"]
    return None, None

def search_collection(name):
    data = tmdb("/search/collection", {"query": name})
    return data["results"][0]["id"] if data and data.get("results") else None

# ─── PRIORITY 3: Plexlist Seeds ─────────────────────────
def scan_filmography(sections, index, taste, rules):
    added = 0
    for stype, name in sections["ACTORS"] + sections["DIRECTORS"]:
        pid, pname = search_person(name)
        if not pid: continue
        
        credits = tmdb(f"/person/{pid}/movie_credits") or {}
        items = credits.get("cast", []) + credits.get("crew", [])
        
        for c in items:
            if stype == "director" and c.get("job") != "Director": continue
            if stype == "actor" and "character" not in c: continue
            tid = c.get("id", 0)
            if tid in index["tmdb_all"]: continue
            
            title = c.get("title", c.get("original_title", ""))
            year = c.get("release_date", "0000")[:4]
            rating = c.get("vote_average", 0)
            
            scores = {}
            scores["same_actor" if stype == "actor" else "same_director"] = BASE_SCORES["same_actor" if stype == "actor" else "same_director"]
            if rating >= 7.5: scores["highly_rated"] = BASE_SCORES["highly_rated"]
            scores["taste_match"] = int(match_taste_profile(taste, c) * 15)
            
            queue = add_candidate({"tmdb_id": tid, "title": title, "year": year}, scores, f"{stype.title()}: {pname}", index)
            if queue: added += 1
            time.sleep(0.12)
        time.sleep(0.3)
    return added

def scan_franchises(sections, index, taste, rules):
    added = 0
    for item in sections["FRANCHISES"]:
        cid = item if isinstance(item, int) else search_collection(item)
        if not cid: continue
        data = tmdb(f"/collection/{cid}")
        if not data: continue
        
        for part in data.get("parts", []):
            tid = part.get("id", 0)
            if tid in index["tmdb_all"]: continue
            
            title = part.get("title", "")
            year = part.get("release_date", "0000")[:4]
            scores = {"franchise_member": BASE_SCORES["franchise_member"], 
                       "taste_match": int(match_taste_profile(taste, part) * 15)}
            queue = add_candidate({"tmdb_id": tid, "title": title, "year": year}, scores, f"Collection: {data.get('name','?')}", index)
            if queue: added += 1
            time.sleep(0.12)
    return added

def scan_genres(sections, index, taste, rules):
    added = 0
    for genre in sections["GENRES"][:5]:
        data = tmdb("/discover/movie", {"with_genres": _genre_id(genre), "sort_by": "popularity.desc", "page": 1})
        if not data: continue
        for m in data.get("results", [])[:8]:
            tid = m.get("id", 0)
            if tid in index["tmdb_all"]: continue
            
            rating = m.get("vote_average", 0)
            scores = {"genre_match": BASE_SCORES["genre_match"]}
            if rating >= 7.5: scores["highly_rated"] = BASE_SCORES["highly_rated"]
            scores["taste_match"] = int(match_taste_profile(taste, m) * 15)
            
            protected = is_protected_genre(genre, rules)
            if protected == "never": continue
            if protected == "always": scores["protected_always"] = BASE_SCORES["protected_always"]
            
            queue = add_candidate({"tmdb_id": tid, "title": m.get("title",""), "year": m.get("release_date","0000")[:4]}, scores, f"Genre: {genre}", index)
            if queue: added += 1
            time.sleep(0.12)
    return added

# ─── PRIORITY 5: Related Content ────────────────────────
def scan_related(sections, index, taste, rules):
    added = 0
    for title in sections["SIMILAR"][:20]:
        m = re.match(r'^(.+?)\s*(?:\((\d{4})\))?\s*$', title)
        s_title = m.group(1).strip() if m and m.group(1) and len(m.group(1)) > 2 else title
        s_year = m.group(2) if m and m.group(2) else None
        
        result = search_movie(s_title, s_year)
        if not result: continue
        
        recs = tmdb(f"/movie/{result['id']}/recommendations") or {}
        for rec in recs.get("results", [])[:6]:
            tid = rec.get("id", 0)
            if tid in index["tmdb_all"]: continue
            
            rating = rec.get("vote_average", 0)
            scores = {"similar_content": BASE_SCORES["similar_content"]}
            if rating >= 7.5: scores["highly_rated"] = BASE_SCORES["highly_rated"]
            scores["taste_match"] = int(match_taste_profile(taste, rec) * 15)
            
            queue = add_candidate({"tmdb_id": tid, "title": rec.get("title",""), "year": rec.get("release_date","0000")[:4]}, scores, f"Similar to: {s_title}", index)
            if queue: added += 1
            time.sleep(0.12)
    return added

# ─── PRIORITY 6: Trending ───────────────────────────────
def scan_trending(sections, index, taste, rules):
    added = 0
    for ep in ["/trending/movie/week", "/movie/popular"]:
        data = tmdb(ep)
        if not data: continue
        for m in data.get("results", [])[:10]:
            tid = m.get("id", 0)
            if tid in index["tmdb_all"]: continue
            
            rating = m.get("vote_average", 0)
            scores = {"trending": BASE_SCORES["trending"]}
            if rating >= 7.5: scores["highly_rated"] = BASE_SCORES["highly_rated"]
            scores["taste_match"] = int(match_taste_profile(taste, m) * 15)
            
            queue = add_candidate({"tmdb_id": tid, "title": m.get("title",""), "year": m.get("release_date","0000")[:4]}, scores, f"Trending", index)
            if queue: added += 1
            time.sleep(0.12)
    return added

# ─── GENRE IDS ──────────────────────────────────────────
_GENRE_IDS = {}
def _genre_id(name):
    if not _GENRE_IDS:
        data = tmdb("/genre/movie/list")
        if data:
            for g in data.get("genres", []): _GENRE_IDS[g["name"].lower()] = g["id"]
    return str(_GENRE_IDS.get(name, ""))

# ─── MAIN ───────────────────────────────────────────────
def main():
    log("=" * 60)
    log(f"DISCOVERY ENGINE v3.0 — Mode: {MODE} — Priority Hierarchy")
    log("=" * 60)
    
    # 1. Load safeguards
    rules = load_rules()
    storage_ok, storage_msg = check_storage(rules)
    health_ok, health_msg = check_health(rules)
    
    log(f"Storage: {storage_msg}")
    log(f"Health:  {health_msg}")
    
    if storage_ok == False:
        log("Storage critical — discovery disabled")
        return
    if health_ok == False:
        log("Health check failed — discovery disabled")
        return
    
    if storage_ok == "reduced":
        log("Storage elevated — reducing discovery rate")
    
        # 2. Refresh taste engine before discovery (so new media is reflected)
    log('Refreshing taste engine...')
    try:
        from discovery.taste import update_all as taste_update
        taste_update('daily')
        log('  Taste updated')
    except Exception as e:
        log(f'  Taste update skipped: {e}')
    
    # 3. Load taste profile
    taste = load_taste()
    
    # Weekly+: update taste from watch history
    if MODE in ("weekly", "monthly", "yearly"):
        update_all()
        taste = load_taste()
        log(f"Taste: {len(taste.get('genres',{}))} genres scored, {taste.get('watched',0)} watched")
    
    # 3. Parse seeds and build index
    sections = parse_plexlist()
    index = build_index()
    log(f"Seeds: {sum(len(v) for v in sections.values())} | Index: {len(index['tmdb_movies'])} movies tracked")
    
    if not TMDB_KEY:
        log("No TMDB_KEY — skipping TMDB scanners")
    
    total = 0
    
    if TMDB_KEY:
        # Discovery hierarchy
        hierarchy = [
            ("P3: Seeds (Filmography)", scan_filmography, not rules.get("complete_only_mode", False)),
            ("P3: Seeds (Franchises)", scan_franchises, True),
            ("P3: Seeds (Genres)",    scan_genres,     not rules.get("complete_only_mode", False)),
            ("P5: Related Content",   scan_related,     MODE in ("daily", "weekly") and not rules.get("complete_only_mode", False)),
            ("P6: Trending",          scan_trending,    MODE in ("daily", "weekly")),
        ]
        
        for label, func, enabled in hierarchy:
            if enabled:
                log(f"--- {label} ---")
                n = func(sections, index, taste, rules)
                total += n
                log(f"  Candidates: {n}")
    
    # 4. Process auto_add queue
    log("--- Processing Auto-Add Queue ---")
    added = process_auto_add(index, radarr_post)
    log(f"  Auto-added to Radarr: {added}")
    
    # 5. Report
    stats = queue_stats()
    log(f"Queues: auto_add={stats.get('auto_add',0)} review={stats.get('review_queue',0)} quarantine={stats.get('quarantine',0)} rejected={stats.get('rejected',0)}")
    log(f"TOTAL: {total} candidates, {added} added to Radarr")
    log("DISCOVERY ENGINE v3 COMPLETE")

if __name__ == "__main__":
    main()
