# FULL TIMER SCHEDULE — All 22 Timers

## Server Timers (18)
```
TIMER                   INTERVAL     PURPOSE
─────────────────────   ────────     ─────────────────────────────────
torrent-doctor          every 10m    Inject 37 trackers, recheck stalled, resume paused
tdarr-post-encode       every 5m     Replace tdarr originals with encoded copies
disk-space-guard        every 15m    Alert on low disk space
health-score            every 30m    Generate Pipeline/state/HEALTH_SCORE.json
balance-8tb             every 30m    Move oldest media 8TB→20TB at >85%, update *arr
seed-finder             every 30m    Re-announce stalled server torrents
smart-fill              every 30m    Add missing episodes when qBit queue <150
disk-watchdog           every 30m    SMART disk health monitoring
crash-watchdog          every 5m     System crash detection + auto-recovery
completed-import        every 2m     Backup import safety net (→ laptop qBit)
protect-8tb             hourly       Disable 8TB *arr root folders at ≥98%
complete-media          every 6h     Find ALL missing seasons/episodes/sequels
auto-dedup              every 6h     Safe full-scan dedup (skips downloads/incomplete)

TASTE:
taste-daily             daily 2:30am Update watch counts + genre scores
taste-weekly            Sun 3am      Director/actor affinity from TMDB
taste-monthly           1st 5am      Full rebuild + score decay
taste-yearly            Jan 1 6am    Complete reset + re-learn

DISCOVERY:
discovery-engine        daily 2am    TMDB scan + scoring + plexlist sync
discovery-weekly        Sun 3am      Deep scan + taste profile update
discovery-monthly       1st 4am      Full sweep
discovery-yearly        Jan 1 5am    Complete refresh

MAINTENANCE:
nightly-backup          daily 3am    Export all configs to /mnt/500gb-1/
pipeline-gc             daily 4am    Cleanup old candidates, compress logs
pipeline-dashboard      always-on    GUI dashboard on port 8090
```

## Laptop Timers (6)
```
TIMER                   INTERVAL     PURPOSE
─────────────────────   ────────     ─────────────────────────────────
vpn-watchdog            every 60s    Restart gluetun if unhealthy
cleanup-completed       every 5m     Remove completed torrents from qBit after import
guard-local-downloads   every 5m     Alert if downloads appear in local Downloads (NOT NFS)
seed-finder             every 10m    Re-announce stalled laptop torrents
healer-check            every 5m     Health check server services (SSH)
laptop-guard            every 30m    Disk space + NFS mount health
healer-backup           daily        Laptop config backup rotation
```

## Timer Status Commands
```bash
# List all pipeline timers
ssh server systemctl list-timers | grep -E 'torrent|tdarr|balance|nightly|discovery|seed|health|complete|smart|cleanup|protect|taste|auto-dedup'

# Check specific timer
ssh server systemctl status torrent-doctor.timer

# Stop/start a timer
ssh server sudo systemctl stop balance-8tb.timer
ssh server sudo systemctl start balance-8tb.timer
```
