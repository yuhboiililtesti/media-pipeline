# Homelab Media Pipeline v7.1

Autonomous media pipeline: download → sort → transcode → serve.  

## What This Does

- **Downloads** via qBittorrent (routed through AirVPN WireGuard)
- **Sorts** automatically: movies vs TV episodes (robust detection, no misclassification)
- **Imports** into Radarr/Sonarr → renamed → Plex notified
- **Transcodes** to HEVC via Tdarr + NVENC
- **Deduplicates** across drives (daily scan, 132GB+ recovered)
- **Self-heals**: auto-restarts failed containers every 5 min
- **Backfills**: searches for missing content when queue is low

## Hardware

|---------|------|-----|-----|-----|

## Quick Start

```bash
# Clone
git clone <repo-url> ~/homelab-pipeline
cd ~/homelab-pipeline

# Deploy to server
scp -r scripts/* server:/opt/
ssh server "sudo systemctl enable --now autonomous-pipeline.timer batch-import.timer health-monitor.timer anti-seed.timer"

# Deploy configs (secrets removed — fill in your own)
scp configs/docker-compose.yml server:/mnt/20TB/homelab/media/compose/
```

## Directory Structure

```
homelab-pipeline/
├── scripts/           # Pipeline scripts (deploy to /opt/)
│   ├── autonomous-pipeline.py   v7.1 master controller
│   ├── batch_import.py          v3: correct sorting + dedup
│   ├── anti-seed.py             v2: dead/zero-seed cleanup
│   ├── health-monitor.py        Container health check
│   ├── dedupe_media.py          Cross-drive deduplication
│   ├── recovery.py              Disk vs library audit
│   ├── plexbot.py               Discord bot v2.0
│   └── *.sh                     Helper scripts
├── configs/           # Config templates (SECRETS REMOVED)
│   ├── docker-compose.yml
│   ├── config.env
│   └── systemd/                 Service + timer units
├── docs/              # Full documentation
│   ├── README.md
│   ├── ECOSYSTEM.md
│   ├── RECOVERY.md
│   ├── ISSUES-SOLUTIONS.md
│   ├── CHANGELOG.md
│   └── JARVIS-BLUEPRINT.md
├── backups/           # Config backups
└── .gitignore         # Excludes secrets
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Plex | 32400 | Media server |
| qBittorrent | 8083 | Downloads (via VPN) |
| Sonarr | 8989 | TV management |
| Radarr | 7878 | Movie management |
| Prowlarr | 9696 | Indexer hub |
| Tdarr | 8265 | HEVC transcode |
| Overseerr | 5055 | Media requests |
| Cross-seed | 2468 | Cross-tracker seeding |
| FlareSolverr | 8191 | Cloudflare bypass |
| Immich | 2283 | Photo management |

## Timers

| Timer | Interval | What |
|-------|----------|------|
| anti-seed | 2 min | Clean dead torrents |
| autonomous-pipeline | 10 min | Full pipeline cycle |
| batch-import | 30 min | Sort downloads to media dirs |
| health-monitor | 5 min | Restart failed containers |
| recovery-sync | daily | Disk vs library audit |
| media-dedupe | daily | Cross-drive dedup |

## Security

- SSH: key-based only (ed25519), password auth disabled
- Firewall: nftables (policy DROP) + UFW, LAN-only ports
- Secrets: stored in .env and config.json (perms 600), NOT in git
- VPN: AirVPN WireKill for all torrent traffic

## Recovery

See [RECOVERY.md](docs/RECOVERY.md) for complete rebuild from bare metal.

## License

MIT — use freely, no warranty.
