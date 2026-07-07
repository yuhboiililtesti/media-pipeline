#!/usr/bin/env python3
# discovery/scoring.py — Confidence scoring + 4-tier queue management
# Queues: auto_add (>80%), review (50-80%), quarantine (30-50%), reject (<30%)

import json, os, re, time
from datetime import datetime

CANDIDATES = "/mnt/20TB/homelab/media/Pipeline/candidates"
AUTO    = f"{CANDIDATES}/auto_add.txt"
REVIEW  = f"{CANDIDATES}/review_queue.txt"
QUAR    = f"{CANDIDATES}/quarantine.txt"
REJECT  = f"{CANDIDATES}/rejected.txt"
DOWNLOADED = f"{CANDIDATES}/downloaded.txt"

# Base scores
BASE_SCORES = {
    "manual_request":      100,
    "missing_monitored":    90,
    "franchise_member":     80,
    "same_director":        70,
    "same_actor":           50,
    "similar_content":      45,
    "genre_match":          35,
    "taste_match":          15,
    "highly_rated":         20,
    "trending":             25,
    "new_release":          15,
    "upcoming":             10,
    "protected_always":     30,  # bonus for "always download" rules
}

# Confidence thresholds
AUTO_THRESHOLD   = 80   # ≥80% confidence → auto-add
REVIEW_THRESHOLD = 50   # ≥50% → review
QUAR_THRESHOLD   = 30   # ≥30% → quarantine

MAX_RAW_SCORE = 200  # theoretical max for percentage calc

def compute_confidence(scores_dict):
    """Compute confidence percentage from a dict of score categories"""
    raw = sum(scores_dict.values())
    # Map to 0-100% confidence
    confidence = min(raw / MAX_RAW_SCORE * 100, 100)
    return round(confidence, 1), raw

def get_queue(confidence):
    if confidence >= AUTO_THRESHOLD:
        return "auto_add"
    elif confidence >= REVIEW_THRESHOLD:
        return "review"
    elif confidence >= QUAR_THRESHOLD:
        return "quarantine"
    return "reject"

def queue_path(queue_name):
    return f"{CANDIDATES}/{queue_name}.txt"

def is_already_queued(tmdb_id):
    for q in ["auto_add.txt", "review_queue.txt", "quarantine.txt", "rejected.txt", "downloaded.txt"]:
        qp = f"{CANDIDATES}/{q}"
        if os.path.exists(qp):
            for line in open(qp):
                if f"TMDB:{tmdb_id}" in line:
                    return True
    return False

def add_candidate(item, scores_dict, reason, index):
    """Score and queue a candidate"""
    tmdb_id = item.get("tmdb_id", 0)
    title   = item.get("title", "?")
    year    = item.get("year", "?")
    
    if is_already_queued(tmdb_id):
        return None
    
    confidence, raw = compute_confidence(scores_dict)
    queue = get_queue(confidence)
    
    entry = f"[{confidence:5.1f}% | {raw:3d}] {title} ({year}) — {reason}  TMDB:{tmdb_id}"
    qp = queue_path(queue)
    
    os.makedirs(os.path.dirname(qp), exist_ok=True)
    with open(qp, "a") as f:
        f.write(entry + "\n")
    
    return queue

def process_auto_add(index, radarr_post_fn):
    """Add auto_add candidates to Radarr"""
    if not os.path.exists(AUTO):
        return 0
    
    lines = [l.strip() for l in open(AUTO) if l.strip()]
    added = 0
    to_keep = []
    
    for line in lines:
        m = re.search(r'TMDB:(\d+)', line)
        if not m: 
            to_keep.append(line)
            continue
        
        tmdb_id = int(m.group(1))
        if tmdb_id in index.get("tmdb_movies", set()):
            # Already in Radarr — move to downloaded
            with open(DOWNLOADED, "a") as f: f.write(line + "\n")
            continue
        
        title_m = re.match(r'\[\s*[\d.]+%\s*\|\s*\d+\]\s+(.+?)\s+\((\d{4})\)', line)
        title = title_m.group(1) if title_m else "Unknown"
        year = int(title_m.group(2)) if title_m else 0
        
        payload = {
            "tmdbId": tmdb_id, "title": title, "year": year,
            "qualityProfileId": 6, "monitored": True,
            "rootFolderPath": "/mnt/20TB/Movies 1",
            "addOptions": {"searchForMovie": True}
        }
        
        result = radarr_post_fn("/movie", payload)
        if result and result.get("id"):
            index["tmdb_movies"].add(tmdb_id)
            with open(DOWNLOADED, "a") as f: f.write(line + "\n")
            added += 1
            time.sleep(0.3)
        else:
            to_keep.append(line)
    
    # Rewrite with remaining
    with open(AUTO, "w") as f:
        for l in to_keep:
            f.write(l + "\n")
    
    return added

def queue_stats():
    stats = {}
    for q in ["auto_add", "review_queue", "quarantine", "rejected", "downloaded"]:
        qp = queue_path(q)
        stats[q] = len(open(qp).readlines()) if os.path.exists(qp) else 0
    return stats
