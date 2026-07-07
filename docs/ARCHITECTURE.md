# Pipeline-Doc — ARCHITECTURE

```
                         REQUEST LAYER
 ┌───────────────┬───────────────┬───────────────────┐
 │  Overseerr    │  plexlist.txt │  Discovery Engine  │
 │  (manual)     │  (curation)   │  (automatic, 2am) │
 └───────┬───────┴───────┬───────┴─────────┬─────────┘
         │               │                 │
         └───────────────┼─────────────────┘
                         ▼
              Radarr / Sonarr / Prowlarr
                         │
                         ▼
                    DOWNLOAD LAYER
 ┌────────────────────────────────────────────┐
 │  LAPTOP (10.0.0.234)                      │
 │  ┌──────────────────────────────────┐     │
 │  │ gluetun — AirVPN WireGuard       │     │
 │  │  FIREWALL=on (killswitch)        │     │
 │  │  Port: 51413 torrent, 8080 WebUI │     │
 │  │  ┌────────────────────────────┐  │     │
 │  │  │ qBittorrent v4.6.3         │  │     │
 │  │  │  DL:22 Tor:650 Cache:2GB   │  │     │
 │  │  │  Save: /downloads → NFS    │  │     │
 │  │  └──────────┬─────────────────┘  │     │
 │  └─────────────┼────────────────────┘     │
 └────────────────┼──────────────────────────┘
                  │ NFS write
 ┌────────────────▼──────────────────────────┐
 │  SERVER /mnt/20TB/homelab/media/downloads │
 └───────────────────────────────────────────┘
                  │
             IMPORT LAYER
  Radarr/Sonarr detect → import to media folder
  → removeCompleted=TRUE → qBit torrent removed
                  │
             MEDIA LAYER
 ┌──────────────────────────────────────────┐
 │  Plex (517 movies, 468 shows)            │
 │  GPU transcode: RTX 3090 Ti NVENC        │
 │  Transcode temp: /tmp (RAM, 7.8GB)       │
 │  tdarr: HEVC encode (midnight-10am)      │
 │  Bazarr: subtitles                       │
 │  decluttarr: cleanup                     │
 │  cross-seed: tracker matching            │
 └──────────────────────────────────────────┘
                  │
             STREAM LAYER
   Remote → port 32400 → Plex
```

## Priority Hierarchy (Discovery Engine)
```
P1: Manual requests (Overseerr)           → 100 pts → auto-add
P2: Missing monitored (RSS/backlog)       → 90 pts  → *arr handles
P3: Plexlist seeds                        → 35-80   → scored + queued
    @Actor:50  @Director:70  +Franchise:80  %Genre:35  ~SimilarTo:45
P4: Library gaps (franchise/collection)   → 80 pts
P5: Related content (TMDB similar)        → 40-55
P6: Trending (TMDB trending/popular)      → 25-45
P7: Taste recommendations (learned)       → 15-35

Confidence → Queue:
  ≥80% → auto_add → Radarr (monitored + searched)
  50-80% → review_queue
  30-50% → quarantine
  <30% → rejected
```

## Data Flow
```
User watches in Plex
  → Taste engine records genres
  → Weekly: profile updated
  → Discovery engine uses taste scores
  → Recommendations become personalized

Media completed (download + import)
  → sync-plexlist marks # in plexlist.txt
  → Plex auto-scans
  → Poster/art fetched
  → tdarr encodes overnight
```
