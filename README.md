# media-pipeline

A self-driving media pipeline for Plex. Finds content you'll actually like, downloads it, imports it, encodes it, and keeps itself running. Built for my homelab, shared in case it helps yours.

## Features

- **Content discovery** — scans TMDB using your taste profile (actors, directors, genres, franchises you like)
- **Gap filling** — finds missing episodes, seasons, sequels, and franchise holes
- **Dual VPN download** — two qBittorrent instances behind WireGuard with automatic failover
- **Auto-import** — completed downloads hit Plex within a minute
- **Space-saving encode** — Tdarr re-encodes to HEVC via NVENC or CPU (~40% smaller)
- **Self-healing** — 9 watchdog timers handle crashes, stalls, duplicates, corrupted files, and disk pressure
- **Scheduled modes** — goes full speed while you sleep, chills during the day

## Quick Start

```bash
git clone https://github.com/yuhboiililtesti/media-pipeline
cd media-pipeline
```

1. Set your API keys in the scripts (search for `YOUR_` placeholders)
2. Point paths to your media drives
3. Get a free TMDB API key from themoviedb.org
4. Install the systemd units:

```bash
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pipeline-max.timer pipeline-day.timer
```

5. Seed your taste profile in `plexlist.txt`:

```
[ACTORS]
@Tom Hanks
@Cate Blanchett

[DIRECTORS]
@Denis Villeneuve
@Hayao Miyazaki

[FRANCHISES]
+10    # Star Wars
+13151 # Marvel

[GENRES]
%Science Fiction
%Horror

[SIMILAR]
~Inception
~Arrival
```

## Commands

**Modes**
```bash
pipeline max        # 50 concurrent downloads
pipeline hard       # 20 concurrent
pipeline med        # 3 concurrent (home hours)
pipeline soft       # pause everything
pipeline status     # current stats
```

**Content**
```bash
pipeline-grow       # discover new content (TMDB + taste)
pipeline-backlog    # fill missing episodes and sequels
pipeline-flow       # max mode + backlog + grow
pipeline-scan       # force Plex library refresh
pipeline-import     # force import completed downloads
pipeline-queue      # show what's in the download queue
```

**Maintenance**
```bash
pipeline-clean      # remove dead torrents + free system space
pipeline-seed       # inject trackers + re-announce everything
pipeline-dedup      # scan for duplicate media files
pipeline-taste      # refresh taste profiles from Plex library
pipeline-daily      # run all daily maintenance tasks
pipeline-log        # quick peek at all logs
```

**Diagnostics**
```bash
pipeline-health     # quick health overview
pipeline-audit      # full system audit
pipeline-stall      # figure out why downloads stopped
pipeline-peers      # seed/peer stats per qBit instance
pipeline-vpn        # check both VPN connections
pipeline-space      # disk usage breakdown
```

**Emergency**
```bash
pipeline-unstall    # restart everything + recover + reseed
pipeline-recover    # NFS remount, compose validate, restart containers
pipeline-config     # change settings on the fly
pipeline-help       # full reference with examples
```

## Self-Healing

| Problem | Guard | Runs |
|---|---|---|
| Dead Docker container | `container-watchdog` | every 5min |
| System crash | `crash-watchdog` | every 5min |
| Torrent stuck at 99% | `stalled-rescue` | every 15min |
| Same episode downloaded twice | `anti-dupe` | every 30min |
| Disk filling up (20TB) | `protect-20tb` | every 30min |
| Disk filling up (8TB) | `protect-8tb` | hourly |
| Fake/corrupt media files | `integrity-check` | daily 3:30am |
| VPN dropped | `vpn-watchdog` (laptop) | every 60s |
| Low disk space | `disk-space-guard` | every 15min |

## Auto Schedule

```
04:00   pipeline max     full speed while everyone sleeps
12:00   pipeline med     chill mode for home hours
02:00   discovery        TMDB scan for new content
03:00   nightly backup   config export to secondary machine
03:30   integrity check  scan for bad files
Sun 03  auto-dedup       weekly duplicate cleanup
```

## Architecture

```
                   ┌─ Prowlarr (8 indexers)
                   │
Request ──→ Radarr/Sonarr ──→ qBit (VPN) ──→ Download complete
                   │                              │
                   │                         Auto-import (1min)
                   │                              │
                   │                           Plex ──→ Tdarr (HEVC encode)
                   │                              │
                   └── Discovery Engine ◄── Taste Profile
                        (TMDB scan)           (plexlist.txt)
```

## Dependencies

- Linux with systemd and Docker
- Radarr, Sonarr, Prowlarr (Docker containers on a shared network)
- Plex Media Server
- qBittorrent (ideally two instances behind VPNs)
- Python 3 (for scripts)
- TMDB API key (free)
- NVIDIA GPU optional (for hardware-accelerated Tdarr encoding)

## Config Files

| File | Purpose |
|---|---|
| `safeguards/rules.json` | Thresholds, limits, content filters |
| `plexlist.txt` | Your content + taste seeds |
| `taste/*.json` | Per-user genre/actor/director scores |
| `systemd/` | All timer and service unit files |
| `scripts/` | Automation scripts (drop-in, edit paths) |
| `discovery/` | TMDB discovery engine with scoring |

## License

MIT
