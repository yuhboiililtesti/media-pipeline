# media-pipeline

Self-driving media pipeline for Plex. Finds content, downloads it through VPNs, imports to Plex, encodes to HEVC, and keeps itself alive.

## Current State (live deployment)

- **1,200+ torrents** across two qBittorrent instances behind WireGuard VPNs
- **2,187 movies** tracked in Radarr (300+ downloaded)
- **2,200+ TV episodes** across 200+ shows in Sonarr
- **~10 MB/s** average download speed (VPN-limited)
- **25 automation engines** running on systemd timers
- **9 guard layers** watching for failures
- **Zero failed services** at steady state
- **Plex grows automatically** — 1-5 new movies per 30-minute cycle

## Quick Start

```bash
git clone https://github.com/yuhboiililtesti/media-pipeline
cd media-pipeline
cp .env.example .env  # fill in your API keys
```

Then read `docs/SETUP.md` for the full walkthrough.

## How It Works

### Download Flow
```
Request → Radarr/Sonarr → Prowlarr (8 indexers) → qBit (VPN)
  → Download complete → Auto-import (1 min) → Plex
  → Radarr/Sonarr removes torrent → next cycle begins
```

### Discovery Flow (every 30 min)
```
Plexlist seeds (40 taste profiles)
  → TMDB scan (actors, directors, franchises, genres)
  → Confidence scoring (0-100%)
  → Auto-add (≥60%) or review queue
  → Radarr searches → qBit downloads → Plex gets it
```

### Plexlist — Your Taste Profile
The pipeline learns what you like from `plexlist.txt`:

```
[ACTORS]         @Tom Hanks, @Morgan Freeman...
[DIRECTORS]      @Christopher Nolan, @Denis Villeneuve...
[FRANCHISES]     +10 (Star Wars), +13151 (Marvel)...
[GENRES]         %Science Fiction, %Horror, %Documentary...
[SIMILAR]        ~Inception, ~The Matrix...
```

The discovery engine scans TMDB for everything these people have made, every movie in these franchises, and similar content — then scores and adds the good stuff automatically.

### Filling Gaps (backlog)
- Complete seasons of shows you're watching (not random episodes)
- Sequels and prequels to movies you own
- Missing franchise installments
- Monitored movies waiting for a good release

### Self-Healing Guards
| Guard | Interval | What it does |
|---|---|---|
| container-watchdog | 5 min | Restarts any dead Docker container |
| crash-watchdog | 5 min | Detects system crashes, recovers |
| stalled-rescue | 15 min | Force rechecks torrents stuck at 95%+ |
| anti-dupe | 30 min | Removes same-episode duplicate downloads |
| protect-20tb | 30 min | Slows/stops downloads when 20TB fills |
| protect-8tb | 1 hr | Locks 8TB roots at 98% |
| integrity-check | daily | Detects fake/corrupted/placeholder files |
| disk-space-guard | 15 min | Alerts on low disk |
| nightly-backup | 3am | Exports all configs to secondary machine |

### Automatic Schedule
```
04:00  pipeline max     (DL=50, full speed)
12:00  pipeline med     (DL=3, home hours)
00:30  pipeline-flow    (seed + fill gaps + discover + import + scan)
02:00  discovery        (TMDB scan with taste)
03:00  nightly backup   (config export)
03:30  integrity check  (fake file scan)
```

### Encoding (Tdarr)
- NVENC HEVC via RTX 3090 Ti
- 5 libraries configured (Movies 1/2/4, TV 1/2)
- Cache on 20TB drive at `/mnt/20TB/Encode-Tmp`
- Post-encode script replaces originals every 5 min
- Target: movies → 1080p HEVC, TV → 720p HEVC (~40% space savings)

## Commands

```bash
pipeline soft|med|hard|max    # Download speed
pipeline status               # Current torrent stats
pipeline-grow                 # Discover new content
pipeline-backlog              # Fill gaps
pipeline-flow                 # Full: max + backlog + grow
pipeline-clean                # Remove dead torrents + system cleanup
pipeline-seed                 # Max peer discovery
pipeline-stall                # Diagnose why flow stopped
pipeline-unstall              # Emergency restart everything
pipeline-health               # Quick health check
pipeline-audit                # Full system audit
pipeline-config show          # View all settings
pipeline-help                 # Full command reference
```

## Recovery

```bash
pipeline-recover   # NFS remount + compose validate + restart + MAX
pipeline-unstall   # Emergency nuclear option
```

See `docs/RECOVERY.md` for complete disaster recovery procedures.

## File Layout

```
/mnt/20TB/
├── Movies 1/           # Primary Plex movie library
├── TV Shows 1/         # Primary Plex TV library
├── Encode-Tmp/         # Tdarr transcode cache
└── homelab/media/
    ├── Pipeline/       # All scripts, configs, state
    │   ├── scripts/    # 25+ automation scripts
    │   ├── discovery/  # TMDB engine + scoring
    │   ├── safeguards/ # Storage/health rules
    │   ├── taste/      # Per-user profiles
    │   ├── plexlist.txt
    │   └── have-list.txt
    ├── compose/        # docker-compose.yml + container configs
    └── downloads/      # qBit download directory

/mnt/8TB/
├── Movies 2/           # Overflow movie library
└── TV Shows 2/         # Overflow TV library
```

## Requirements

- Linux server with Docker, systemd, Python 3
- Radarr + Sonarr + Prowlarr (Docker)
- Plex Media Server
- qBittorrent (dual instance recommended — one VPN, one overflow)
- TMDB API key (free)
- NVIDIA GPU optional for Tdarr encoding
- At least one large storage drive

## License

MIT
