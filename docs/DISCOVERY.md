# DISCOVERY ENGINE — v3.0 Complete Reference

## Priority Hierarchy
```
P1: Manual requests (Overseerr)          → 100 pts → auto-add
P2: Missing monitored (RSS/backlog)      → 90 pts  → handled by *arr
P3: Plexlist seeds:
    @Actor:50  @Director:70  +Franchise:80  %Genre:35  ~SimilarTo:45
P4: Library gaps (franchise/collection)  → 80 pts
P5: Related content (TMDB similar)       → 40-55 pts
P6: Trending (TMDB trending/popular)     → 25-45 pts
P7: Taste recommendations (learned)      → 15-35 pts
```

## Confidence → 4 Queues
```
raw_score / 200 * 100 = confidence%

≥80% → auto_add.txt      → Radarr (monitored + searched automatically)
50-80% → review_queue.txt → manual review recommended
30-50% → quarantine.txt   → borderline, held
<30% → rejected.txt       → not added
```

## Seed Types in plexlist.txt
```
# Title (Year)  = owned/tracked (auto-commented by sync-plexlist)
Title (Year)    = wanted (engine adds to Radarr)
@Actor Name     = scan entire filmography (+50 bonus)
@Director Name  = scan entire filmography (+70 bonus)
+TMDB_ID        = complete franchise collection (+80 bonus)
%Genre          = discover by genre (+35 bonus)
~Movie Name     = find similar content (+45 bonus)
```

## Scanner Descriptions
| Scanner | Source | Bonus | Description |
|---------|--------|-------|-------------|
| scan_filmography | TMDB person credits | 50/70 pts | All movies by actor/director |
| scan_franchises | TMDB collection | 80 pts | All movies in franchise |
| scan_genres | TMDB discover | 35 pts | Popular movies by genre |
| scan_similar | TMDB recommendations | 45 pts | Similar to seed movies |
| scan_trending | TMDB trending/popular | 25 pts | Currently trending |
| scan_new_releases | TMDB upcoming | 15 pts | Upcoming theatrical |

## Schedule
| Timer | When | What |
|-------|------|------|
| discovery-engine | Daily 2am | All scanners (respects complete_only mode) |
| discovery-weekly | Sun 3am | Deep scan + taste profile update |
| discovery-monthly | 1st 4am | Full sweep |
| discovery-yearly | Jan 1 5am | Complete refresh |
| scan-now.sh | Manual | Run on demand from command center |

## Complete-Only Mode
```
Enabled in safeguards/rules.json: "complete_only_mode": true

SKIPS:  Actor/director filmographies, genre discovery, trending, similar content
KEEPS:  Franchise gaps, missing seasons/episodes, sequels/prequels to owned content
```

## Taste Integration
```
Taste scores are used as multiplier in candidate scoring:
  taste_match = match_taste_profile(taste, movie) * 15
  Range: 2.25 (0.15*15) to 45 (3.00*15) bonus points
```

## API Functions
```python
from discovery.engine import *
from discovery.scoring import *
from discovery.taste import *

# Parse plexlist
sections = parse_plexlist()  # returns dict of seed categories

# Build index
index = build_index()  # returns {movies, shows, tmdb_movies, tmdb_all}

# Score and queue candidate
scoring.add_candidate(item, scores_dict, reason, index)

# Process auto-add queue
scoring.process_auto_add(index, radarr_post)

# Update taste
taste = update_all('daily')
```
