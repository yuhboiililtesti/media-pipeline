# TASTE ENGINE — v4.0 Complete Reference

## Architecture
```
Plex Watch Data (Movies + TV) ──→ Genre Scores (daily)
TMDB Credits ──→ Director/Actor Scores (weekly)
Radarr Library ──→ Fallback (if Plex down)

All scores: 0.15 (never watch) to 3.00 (favorite), default 1.00 (neutral)

Per-User Profiles ──→ Global Profile (weighted merge)
                           ↓
                    Discovery Engine (taste_match bonus)
```

## Scoring Formula
```
score = watch_count / average_watch_count
Clamped: 0.15 ≤ score ≤ 3.00
```

## Update Schedule
| Timer | When | What |
|-------|------|------|
| smart-fill | Every 30 min | Plex watch counts → genre scores |
| complete-media | Every 6 hours | Genre scores (if new media added) |
| discovery-engine | Daily 2am | Full taste refresh before scanning |
| taste-daily | Daily 2:30am | Standalone daily update |
| taste-weekly | Sun 3am | Director/actor affinity from TMDB |
| taste-monthly | 1st 5am | Full rebuild + score decay |
| taste-yearly | Jan 1 6am | Complete reset + re-learn |

## User Auto-Detection
- Scans Plex `/accounts` on every run
- Any named user → creates `taste/{username}.json` at default 1.00
- New users auto-added to global merge
- Currently: topazconch + astrotopaz (more will appear automatically)

## Score Files
```
taste/global_profile.json  — merged profile
taste/{username}.json      — per-user profiles
taste/cache.json           — TMDB API cache (6 hours)
```

## Defaults
```
DEFAULT_SCORE = 1.00   (unknown genres/directors/actors)
MIN_SCORE = 0.15       (floor — never zero out a genre)
MAX_SCORE = 3.00       (ceiling — prevent runaway scores)
DECAY_FACTOR = 0.80    (monthly decay for unwatched)
```

## API Functions
```python
from discovery.taste import *

# Update taste (pass mode)
update_all('daily')     # Watch counts + genres
update_all('weekly')    # + director/actor from TMDB  
update_all('monthly')   # + rebuild + decay
update_all('yearly')    # + full reset

# Query taste
taste = load_taste()
get_genre_score(taste, 'comedy')     # 0.15-3.00
get_director_score(taste, 'nolan')   # 0.15-3.00
get_actor_score(taste, 'dicaprio')   # 0.15-3.00
match_taste_profile(taste, movie_data)  # overall match 0.15-3.00

# Get similar recommendations
get_similar_recommendations(tmdb_id, taste, limit=5)
```
