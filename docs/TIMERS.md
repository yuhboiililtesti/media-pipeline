# ACTIVE TIMERS — Complete Schedule
# Updated: 2026-07-18 — Pipeline v7.4

---

## SERVER TIMERS (7 active)

| Timer                    | Interval  | Service Type | Script                           | Purpose                              |
|--------------------------|-----------|--------------|----------------------------------|--------------------------------------|
| anti-seed.timer          | every 2m  | oneshot      | /opt/anti-seed.py               | Delete dead/zero-seed torrents       |
| autonomous-pipeline.timer| every 10m | oneshot      | /opt/autonomous-pipeline.py     | v7.3 master controller (14 modules)  |
| health-monitor.timer     | every 5m  | oneshot      | /opt/health-monitor.py          | Auto-restart failed containers       |
| batch-import.timer       | every 30m | oneshot      | /opt/batch_import.py            | v3: Sort downloads to media dirs     |
| classify-media.timer     | every 6h  | oneshot      | /opt/classify_media.py          | v1: Fix misplaced movies/TV shows    |
| recovery-sync.timer      | daily     | oneshot      | /opt/recovery.py                | Disk vs Radarr/Sonarr scan           |
| media-dedupe.timer       | daily     | oneshot      | /opt/dedupe_media.py            | Cross-drive deduplication            |

Also running: unattended-upgrades (daily security patches)

---

## WHAT EACH TIMER DOES

### anti-seed.timer (every 2 min)
- Scans qBit torrents for dead (0 seeds) and very low-seed items
- Deletes only truly dead torrents, not active seeders
- Logs to /mnt/nvme/pipeline-logs/anti-seed.log

### autonomous-pipeline.timer (every 10 min)
14 modules in sequence:
1. DISK GUARD — pause at 98% disk usage, route to 8TB primary
2. QBIT MAX — optimize qBit settings (DHT/PeX/LSD, 5000 conn)
3. ANTI-DUPE — remove duplicate torrents by hash
4. AUDIO GUARD — delete non-English torrents (anime dual-audio kept)
5. LEECH CLEANUP — delete at 100%, pause active seeders
6. DEAD PATROL — remove 0-seed torrents with <5% progress
7. AUTO-IMPORT — hardlink completed downloads to media dirs (correct TV/movie sorting)
8. *ARR TRIGGERS — RefreshMonitoredDownloads + ProcessMonitoredDownloads + RescanSeries
9. SMART FILL — search when queue <80 (MissingMoviesSearch + MissingEpisodeSearch)
10. SEASONAL CASCADE — S01 done -> auto-unlock S02
11. PROWLARR SYNC — fullSync to Radarr + Sonarr
12. PLEX SCAN — refresh Movies + TV Shows libraries
13. DISK PURGE — delete non-English files from media dirs
14. HEALTH CHECK — Docker auto-restart unhealthy containers

### batch-import.timer (every 30 min)
- Scans /downloads for completed torrent folders
- Detects TV vs movies using robust regex (SxxExx, Season X, false-positive exclusions)
- Cross-type dedup: catches movies in TV dirs and vice versa
- Size-based dedup: catches renames across drives
- Moves to media dir (8TB or 20TB based on free space)
- Triggers Plex rescan
- State: /mnt/nvme/pipeline-logs/import_state.json

### health-monitor.timer (every 5 min)
- Checks all 16 Docker containers
- Auto-restarts unhealthy/missing containers
- Logs to /mnt/nvme/pipeline-logs/health-monitor.log

### recovery-sync.timer (daily)
- Scans all media directories on disk
- Compares against Radarr/Sonarr library
- Reports missing content
- State: /mnt/nvme/pipeline-logs/recovery_state.json

### media-dedupe.timer (daily)
- Scans all 4 media dirs (Movies 1, Movies 2, TV Shows 1, TV Shows 2)
- Finds duplicates by filename and size
- Prefers organized subdirectory copies over loose files
- Cross-drive dedup (catches copies across 20TB and 8TB)
- First run: 79 dupes deleted, 132.8 GB recovered
- State: /mnt/nvme/pipeline-logs/dupe_state.json

### classify-media.timer (every 6h) — NEW v7.4
- Scans all Movies and TV Shows directories
- Detects TV shows misplaced in Movies (S##E##, S##., Season #, EP##)
- Detects movies misplaced in TV Shows (year patterns, no TV markers)
- Skips movie extras: featurettes, commentaries, NCOP/NCED, making-of
- Automatically moves misplaced content to correct directory
- Triggers Radarr/Sonarr rescan after moves
- State: /mnt/nvme/pipeline-logs/classify_state.json

---

## LAPTOP TIMER (1 active)

| Timer                    | Interval  | Purpose                            |
|--------------------------|-----------|--------------------------------------|
| health-monitor.timer     | every 5m  | Checks server services, alerts       |

---

## TIMER MANAGEMENT

```bash
# List all active timers
systemctl list-timers --all

# Check specific timer
systemctl status autonomous-pipeline.timer

# Stop/start a timer
sudo systemctl stop anti-seed.timer
sudo systemctl start anti-seed.timer

# View timer logs
journalctl -u autonomous-pipeline --since "1 hour ago"
cat /mnt/nvme/pipeline-logs/import.log
```

---

## TIMERS REMOVED IN v7.1 (from v6.0)

These were consolidated into autonomous-pipeline or removed as unnecessary:
torrent-doctor, tdarr-post-encode, disk-space-guard, health-score,
balance-8tb, seed-finder, disk-watchdog, crash-watchdog,
completed-import, protect-8tb, complete-media, smart-fill,
auto-dedup, discovery-engine, discovery-weekly/monthly/yearly,
taste-daily/weekly/monthly/yearly, nightly-backup, pipeline-gc,
pipeline-dashboard, rapid-cleanup, match-fix, audio-guard,
plexlist-sync
