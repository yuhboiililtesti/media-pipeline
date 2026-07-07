# Pipeline-Doc — AUTOMATION

## Full Timer Inventory

### Server (18 timers)
```
TIMER                    INTERVAL      PURPOSE
torrent-doctor           every 10m     Inject 37 trackers, recheck stalled, resume paused
tdarr-post-encode        every 15m     Replace originals with tdarr encoded copies
disk-space-guard         every 15m     Alert on low disk space
health-score             every 30m     Generate HEALTH_SCORE.json
balance-8tb              every 30m     Move media 8TB→20TB when >85% (Python v2)
seed-finder              every 30m     Re-announce stalled server torrents
disk-watchdog            every 30m     SMART disk health monitoring
crash-watchdog           every 5m      System crash detection + recovery
completed-import         every 2m      Backup import safety net
protect-8tb              hourly        Disable 8TB *arr roots at >98%
complete-media           every 6h      Find all missing seasons/episodes/sequels
discovery-engine         daily 2am     TMDB scan + taste + scoring + plexlist sync
discovery-weekly         Sun 3am       Deep scan + taste profile update
discovery-monthly        1st 4am       Full sweep
discovery-yearly         Jan 1 5am     Complete refresh
nightly-backup           daily 3am     Export all configs to desktop /mnt/500gb-1/
pipeline-gc              daily 4am     Garbage collection (candidates, logs, cache)
pipeline-dashboard       always-on     GUI dashboard on port 8090
```

### Laptop (5 timers)
```
TIMER                    INTERVAL      PURPOSE
vpn-watchdog             every 60s     Restart gluetun if unhealthy
cleanup-completed        every 5m      Remove completed torrents from qBit
seed-finder              every 10m     Re-announce stalled laptop torrents
healer-check             every 5m      Health check server services
healer-backup            daily         Laptop config backup rotation
```

## Scripts (Pipelines/scripts/)
```
torrent-doctor.sh         — Inject trackers + force recheck stalled
tdarr-post-encode.sh      — Replace encoded originals
balance-8tb.sh            — Move media 8TB→20TB (Python)
seed-finder.sh            — Re-announce stalled torrents
health-score.sh           — HEALTH_SCORE.json generator
pipeline-gc.sh            — Cleanup old candidates/logs
nightly-backup.sh         — Full config export + scp to desktop
complete-media.py         — Auto-find missing seasons/episodes/sequels
discovery-engine.py       — Legacy v2 (replaced by discovery/engine.py)
sync-plexlist.py          — Auto-comment downloaded items
dashboard.py              — GUI dashboard (port 8090)
generate-plexlist.sh      — Rebuild plexlist from disk
scan-now.sh               — Manual discovery run
protect-8tb.sh            — Disable 8TB roots at >98%
```

## Torrent Doctor — What It Does (every 10 min)
```
1. Inject 37 public trackers into all torrents
2. Re-announce stalled downloads
3. Force recheck long-stalled (>2 hours)
4. Check for 99.5-100% stuck torrents → force recheck
5. Force resume paused/errored torrents
6. Report DHT health + download speed
```

## Complete Media Engine — What It Does (every 6 hours)
```
P1: Find all shows with missing episodes → trigger season search (top 30)
P2: Trigger MissingMoviesSearch for all 2,000+ missing movies
P3: Scan 20 franchise collections → add missing installments
P4: Scan owned movies for sequels/prequels → auto-add
```

## Discovery Engine — Daily 2am
```
- Parse plexlist.txt (actors, directors, franchises, genres, similar-to)
- Scan TMDB for each seed
- Score candidates (confidence 0-100%)
- Queue: auto_add (≥80%), review (50-80%), quarantine (30-50%), reject (<30%)
- Process auto_add → add to Radarr with search
- Update plexlist.txt with new additions
```
