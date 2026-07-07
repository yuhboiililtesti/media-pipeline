# Media Pipeline — Self-Healing Homelab Automation

A fully autonomous media pipeline that discovers, downloads, imports, encodes, and organizes content — then keeps itself running 24/7 with zero human intervention.

## What It Does

```
Indexer → Radarr/Sonarr → qBittorrent (VPN) → Download → Auto-Import → Plex → Tdarr (encode)
                    ↑                                                              |
                    └──────── Discovery Engine (TMDB + Taste) ←────────────────────┘
```

- **Discovers** new content from TMDB based on your taste (actors, directors, genres, franchises)
- **Downloads** through VPN-secured qBittorrent with dual-client failover
- **Imports** to Plex within 1 minute of completion
- **Encodes** to HEVC saving 40-50% space (NVENC GPU or CPU)
- **Self-heals** — 9 guard layers catch every failure mode
- **Protects** drives from filling up (graceful throttle → pause → stop)

## Quick Start

```bash
# Install pipeline commands (on any machine)
git clone https://github.com/YOUR_USER/pipeline.git
cd pipeline
sudo cp systemd/pipeline-commands.sh /usr/local/bin/

# Basic usage
pipeline-help          # Full command reference
pipeline max           # Start downloading
pipeline-flow          # Full: download + fill gaps + discover new
pipeline-health        # System health check
pipeline-stall         # Diagnose why flow stopped
pipeline-config show   # View all settings
```

## Requirements

- **Server**: Linux with Docker, Python 3, systemd
- **VPN**: WireGuard (AirVPN, Mullvad, or any provider)
- **Media drives**: Mounted at `/mnt/20TB` and `/mnt/8TB` (configurable)
- **Plex**: Installed and running
- **Radarr + Sonarr + Prowlarr**: Docker containers on `media-net`
- **qBittorrent**: Two instances recommended (VPN + overflow)
- **TMDB API key**: Free from https://www.themoviedb.org/settings/api

## Architecture

```
Pipeline/
├── scripts/          # 25 automation scripts
├── discovery/        # TMDB discovery engine v3
├── safeguards/       # Storage + health guards
├── taste/            # Per-user taste profiles
├── systemd/          # All 50+ timer/service units
├── docs/             # Full documentation
├── have-list.txt     # Everything in your Plex
└── plexlist.txt      # Owned content + taste seeds
```

## The 25 Commands

| Command | Does |
|---|---|
| `pipeline soft\|med\|hard\|max` | Download speed control |
| `pipeline status` | Current torrent stats |
| `pipeline-grow` | Discover new content (TMDB + taste) |
| `pipeline-backlog` | Fill missing episodes/sequels |
| `pipeline-flow` | Full: max + backlog + grow |
| `pipeline-clean` | Remove dead torrents + system cleanup |
| `pipeline-seed` | Inject trackers + re-announce all |
| `pipeline-taste` | Refresh taste profiles |
| `pipeline-health` | Full health check |
| `pipeline-audit` | Complete system audit |
| `pipeline-stall` | Diagnostic: why isn't flow working? |
| `pipeline-unstall` | Emergency full restart + recover |
| `pipeline-recover` | Recovery procedures |
| `pipeline-import` | Force import completed downloads |
| `pipeline-scan` | Force Plex library refresh |
| `pipeline-queue` | Show download queues |
| `pipeline-peers` | Seeder/peer statistics |
| `pipeline-vpn` | VPN connection status |
| `pipeline-space` | Disk space deep dive |
| `pipeline-log` | Quick log overview |
| `pipeline-daily` | Run all daily maintenance |
| `pipeline-dedup` | Run deduplication |
| `pipeline-encode` | Tdarr encoding status |
| `pipeline-config` | Change any setting |
| `pipeline-help` | Full command reference |

## Self-Healing Guards (9 layers)

| Guard | Frequency | Protects Against |
|---|---|---|
| crash-watchdog | 5min | System crash detection |
| container-watchdog | 5min | Dead Docker containers |
| stalled-rescue | 15min | Torrents stuck at 95%+ |
| anti-dupe | 30min | Same-episode duplicate downloads |
| protect-20tb | 30min | 20TB drive filling up |
| protect-8tb | 1hr | 8TB drive filling up |
| integrity-check | daily | Fake/corrupted/placeholder files |
| disk-space-guard | 15min | Low disk alerts |
| nightly-backup | daily 3am | Full config export |

## Auto-Schedule

```
4:00am  — MAX mode (DL=50, work hours)
12:00pm — MED mode (DL=3, home hours)
2:00am  — Discovery engine (TMDB scan)
3:00am  — Nightly backup
3:30am  — Integrity check
Sun 3am — Weekly dedup
```

## Configuration

Edit `safeguards/rules.json`:
```json
{
  "auto_add_threshold": 60,
  "max_per_day": {"movies": 25, "shows": 10},
  "never_add": "",
  "complete_only_mode": false
}
```

Edit `plexlist.txt` to add taste seeds:
```
[ACTORS]
@Tom Hanks
@Christopher Nolan

[GENRES]
%Science Fiction
%Horror
```

## License

MIT — use it, modify it, share it. Just don't blame me if it downloads the entire internet.
