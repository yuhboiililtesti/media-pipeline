# sync-plexlist.sh — Auto-update plexlist.txt from Radarr/Sonarr
# Runs after discovery-engine, marks downloaded content with #

import json, urllib.request, re, time

PLEXLIST = "/mnt/20TB/homelab/media/Pipeline/plexlist.txt"
RADARR_URL = "http://localhost:7878/api/v3"
SONARR_URL = "http://localhost:8989/api/v3"
RADARR_KEY = "YOUR_RADARR_API_KEY"
SONARR_KEY = "YOUR_SONARR_API_KEY"

def radarr_get(path):
    url = f"{RADARR_URL}{path}?apikey={RADARR_KEY}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())

def sonarr_get(path):
    url = f"{SONARR_URL}{path}?apikey={SONARR_KEY}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())

def extract_title_year(line):
    """Extract title and year from a plexlist line like 'Movie Name (2020)'"""
    line = line.lstrip("# ").strip()
    m = re.match(r'^(.+?)\s*\((\d{4})\)', line)
    if m:
        return m.group(1).strip().lower(), m.group(2)
    return line.lower(), None

# Get all downloaded movies from Radarr
print("Fetching Radarr movies with files...")
movies = radarr_get("/movie") or []
downloaded = {m["title"].lower().strip(): m for m in movies if m.get("hasFile")}
print(f"  Downloaded: {len(downloaded)} of {len(movies)} movies")

# Get all downloaded shows from Sonarr
print("Fetching Sonarr shows with files...")
shows = sonarr_get("/series") or []
dl_shows = {s["title"].lower().strip(): s for s in shows if s.get("statistics", {}).get("episodeFileCount", 0) > 0}
print(f"  Downloaded: {len(dl_shows)} of {len(shows)} shows")

# Process plexlist.txt
print("Processing plexlist.txt...")
lines = open(PLEXLIST).read().splitlines()
new_lines = []
current = None
commented_new = 0

for line in lines:
    stripped = line.strip()
    
    # Track sections
    m = re.match(r'\[(MOVIES|SHOWS|ACTORS|DIRECTORS|FRANCHISES)\]', stripped)
    if m:
        current = m.group(1)
        new_lines.append(line)
        continue
    
    # Skip non-content lines
    if not stripped or stripped.startswith("#") and not stripped.startswith("# @"):
        new_lines.append(line)
        continue
    
    if current == "MOVIES":
        title, year = extract_title_year(stripped)
        if title in downloaded:
            # This movie is now downloaded — comment it out
            leading = line[:len(line) - len(line.lstrip())]
            content = line.lstrip()
            new_lines.append(f"{leading}# {content}")
            commented_new += 1
        else:
            new_lines.append(line)
    elif current == "SHOWS":
        title = stripped.lower()
        if title in dl_shows:
            leading = line[:len(line) - len(line.lstrip())]
            content = line.lstrip()
            new_lines.append(f"{leading}# {content}")
            commented_new += 1
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(PLEXLIST, "w") as f:
    f.write("\n".join(new_lines))

print(f"Commented {commented_new} newly-downloaded items")
print("Done")
