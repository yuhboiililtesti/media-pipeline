# Pipeline Commands — Complete Reference

## Mode Control
```bash
pipeline soft        Pause ALL downloads (DL=0)
pipeline med         Normal mode (DL=3, home hours)
pipeline hard        Fast mode (DL=20)
pipeline max         Maximum speed (DL=50, Tor=500, Conn=400)
pipeline status      Current stats on both qBits
```

## Content Discovery
```bash
pipeline-grow        Discover NEW content (TMDB + 40 taste seeds + Radarr search)
pipeline-backlog     Fill gaps (missing episodes, sequels, franchise completions)
pipeline-flow        Full pipeline: max mode + backlog + grow + import + scan
pipeline-scan        Force Plex library refresh
pipeline-import      Force import completed downloads to Plex
pipeline-queue       Show Radarr/Sonarr download queue
```

## Maintenance
```bash
pipeline-clean       Remove dead torrents + system cleanup (pacman, journals, coredumps)
pipeline-seed        Inject 14 trackers + re-announce all + resume paused
pipeline-dedup       Run media deduplication scan
pipeline-encode      Tdarr encoding status + post-encode
pipeline-taste       Refresh taste profiles from Plex library
pipeline-log         Tail all pipeline logs
pipeline-daily       Run full daily maintenance (6 steps)
```

## Monitoring
```bash
pipeline-health      Quick health check (disk, docker, services, downloads)
pipeline-audit       Complete system audit
pipeline-stall       Diagnostic: why isn't pipeline flowing?
pipeline-peers       DHT nodes, seeds, peers, trackers per qBit
pipeline-vpn         VPN connection status
pipeline-space       Disk space breakdown
```

## Emergency
```bash
pipeline-unstall     Restart everything + recover + reseed
pipeline-recover     NFS remount + compose validate + restart containers
pipeline-config      Master settings hub
pipeline-sync        Push current pipeline to GitHub (sanitized)
pipeline-help        Full command reference
```

## Auto-Flow Timer
```bash
pipeline-flow        Runs every 30 min automatically:
  1. pipeline-seed       (max peer discovery)
  2. complete-media      (fill all gaps)
  3. discovery-engine    (TMDB scan, find new content)
  4. pipeline-import     (force import completed)
  5. pipeline-scan       (refresh Plex)
```
