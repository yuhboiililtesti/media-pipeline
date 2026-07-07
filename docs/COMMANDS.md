# Pipeline-Doc — COMMANDS v4.0

## Quick Access
```bash
ssh server          # Server shell
ssh laptop          # Laptop shell
ssh desktop         # Desktop shell (port <ssh-port>)
```

## Pipeline Command Suite (25 commands)

### Mode Control
```bash
pipeline soft       # Pause all downloads (gaming, DL=0)
pipeline med        # Normal mode (DL=3, Tor=15, Conn=100)
pipeline hard       # Fast mode (DL=20, Tor=200, Conn=300)
pipeline max        # Maximum speed (DL=50, Tor=500, Conn=400)
pipeline status     # Full torrent stats on both qBits
```

### Content Discovery
```bash
pipeline-grow       # Discover NEW content (TMDB scan + taste + add to Radarr)
pipeline-backlog    # Fill all gaps (missing episodes, sequels, franchise completions)
pipeline-flow       # Full pipeline: max mode + backlog + grow
pipeline-scan       # Force Plex library scan for new content
pipeline-import     # Force import completed downloads to Plex
pipeline-queue      # Show Radarr/Sonarr download queue status
```

### Seeding & Peers
```bash
pipeline-seed       # Inject 15 trackers + re-announce all + resume paused
pipeline-peers      # Show DHT nodes, seeds, peers, tracker count per qBit
```

### Maintenance
```bash
pipeline-clean      # Remove dead 0-seed torrents + system cleanup (pacman, journals, coredumps)
pipeline-dedup      # Run media deduplication scan
pipeline-encode     # Check Tdarr encoding status + run post-encode
pipeline-taste      # Refresh taste profiles with current library stats
pipeline-log        # Show last line of all pipeline logs
pipeline-daily      # Run full daily maintenance (all 6 steps)
```

### Monitoring
```bash
pipeline-health     # Full health check (disk, docker, services, Plex, downloads)
pipeline-audit      # Complete system audit (everything)
pipeline-vpn        # Check both VPN connections (laptop + overflow)
pipeline-space      # Disk space report with top folders
```

### Recovery
```bash
pipeline-recover    # NFS remount, compose validate, restart stuck containers, re-apply MAX
pipeline-help       # Show all commands
pipeline-config     # Master settings hub (change any setting)
```

## pipeline-config — Change Any Setting
```bash
pipeline-config show                        # Show all current settings
pipeline-config mode soft|med|hard|max      # Download speed
pipeline-config import 1|2|5                # Import check interval (min)
pipeline-config doctor 5|10|15              # Torrent doctor interval (min)
pipeline-config dedup daily|weekly|off      # Dedup frequency
pipeline-config grow daily|weekly|now       # Discovery frequency
pipeline-config threshold 50-99             # Auto-add confidence %
pipeline-config save                        # Backup all commands to Pipeline/backups/
```

## Auto-Schedule (runs automatically)
```
4:00am  — pipeline max (DL=50, work hours)
12:00pm — pipeline med (DL=3, home hours)
2:00am  — discovery-engine (TMDB scan + taste scoring)
3:00am  — nightly-backup (export all configs to desktop)
3:30am  — integrity-check (detect fake/corrupted files)
4:30am  — auto-dedup (weekly Sunday only)
```

## Web UIs
```
Dashboard:  http://<server-ip>:8090
qBit:       http://<laptop-ip>:8080 (laptop VPN)
Overflow:   http://<server-ip>:8083 (server VPN)
Radarr:     http://<server-ip>:7878
Sonarr:     http://<server-ip>:8989
Prowlarr:   http://<server-ip>:9696
Plex:       http://<server-ip>:32400
Overseerr:  http://<server-ip>:5055
Tdarr:      http://<server-ip>:8265
```

## Manual Actions
```bash
# Run discovery with TMDB
ssh server TMDB_KEY=5e00e3a8059e33e9f559bf884ed726ed python3 /mnt/20TB/homelab/media/Pipeline/discovery/engine.py daily

# Force import scan
ssh server curl -X POST 'http://localhost:7878/api/v3/command?apikey=YOUR_RADARR_API_KEY' -H 'Content-Type:application/json' -d '{"name":"DownloadedMoviesScan","importMode":"move"}'

# Check Radarr queue
ssh server curl -s 'http://localhost:7878/api/v3/queue?apikey=YOUR_RADARR_API_KEY' | python3 -m json.tool

# Clear qBit completed torrents
ssh laptop python3 /home/laptop/pipeline/cleanup-completed.sh

# Restart Plex
ssh server sudo systemctl restart plexmediaserver
```

## Logs
```bash
ssh server ls /mnt/20TB/homelab/media/Pipeline/logs/
ssh server tail -50 /mnt/20TB/homelab/media/Pipeline/logs/discovery-engine.log
ssh server tail -20 /mnt/20TB/homelab/media/Pipeline/logs/torrent-doctor.log
ssh server tail -20 /mnt/20TB/homelab/media/Pipeline/logs/nightly-backup.log
ssh server tail -20 /mnt/20TB/homelab/media/Pipeline/logs/auto-import.log
```

## Service Control
```bash
# Restart a timer
ssh server sudo systemctl restart torrent-doctor.timer

# Check service status
ssh server systemctl status pipeline-dashboard

# Disable a timer
ssh server sudo systemctl stop auto-dedup.timer

# View journal
ssh server sudo journalctl -u pipeline-dashboard -n 30

# List all pipeline timers
ssh server systemctl list-timers --no-pager | grep -E 'pipeline|torrent|tdarr|balance|nightly|discovery|seed|health|complete|cleanup|protect|taste|auto-dedup|smart|shadow|quality|safe|anti|guard|integrity|crash|mark'
```
