# HOMELAB MEDIA PIPELINE — PIPELINE-DOC v3.2

## Quick Reference
```
Dashboard:  http://<server-ip>:8090
qBit:       http://<laptop-ip>:8080 (topaz / see info file)
Radarr:     http://<server-ip>:7878
Sonarr:     http://<server-ip>:8989
Prowlarr:   http://<server-ip>:9696
Plex:       http://<server-ip>:32400
Overseerr:  http://<server-ip>:5055
Tdarr:      http://<server-ip>:8265

Server SSH: <user>@<server-ip> -p 2223
Laptop SSH: laptop@<laptop-ip> -p 2225
```

## Machines

### Server (<server-ip>) — Arch Linux
- GPU: RTX 3090 Ti (NVENC)
- Root: 86.8G ext4 LVM (69%)
- Drives: 20TB (60%, 7.5TB free NTFS), 8TB (91%, 744GB free NTFS), NVMe (RETIRED)
- Docker: 10 containers on media-net
- Plex metadata: /var/lib/plex (SSD ext4)

### Laptop (<laptop-ip>) — Ubuntu 24.04
- Dual-core, 3.7GB RAM, 232GB HDD
- Ethernet only (enp8s0, static <laptop-ip>), WiFi DISABLED
- qBit: DL:22, Tor:650, Cache:2048MB, DHT:360
- VPN: AirVPN WireGuard (<vpn-public-ip> Toronto)
- NEVER: set qBit save path to /config/Downloads (use /downloads = NFS)
- Guard: guard-local-downloads.timer (every 5m) + laptop-guard.timer (every 30m)

### Desktop (<desktop-ip>) — CachyOS
- Admin workstation, backup target
- /mnt/500gb-1/homelab-backup/

## Pipeline Directory
```
/mnt/20TB/homelab/media/Pipeline/
├── discovery/         v3.0 engine (priority hierarchy, 4 queues)
├── safeguards/        storage/health guard + circuit breakers
├── taste/             per-user taste profiles (topazconch, astrotopaz)
├── candidates/        706 quarantine, 77 review, 28 rejected
├── scripts/           17 automation scripts
├── knowledge/         institutional memory
├── logs/              unified logging
├── state/             HEALTH_SCORE.json, state snapshots
├── plexlist.txt       3,234 lines master content seed
├── taste_profile.json global taste data
└── KNOWN_BAD.md       institutional memory
```

## Download Flow
```
Request → Radarr/Sonarr → Prowlarr → 10 indexers → qBit (laptop VPN)
  → NFS write to server 20TB → Radarr detects (~1 min)
  → Import to media folder → Remove from qBit → Plex scans → Stream
```

## Automation (18 timers active)
```
Server: torrent-doctor(10m), tdarr-post(15m), balance-8tb(30m),
        seed-finder(30m), health-score(30m), disk-guard(15m),
        discovery(daily 2am), nightly-backup(daily 3am),
        complete-media(6h), protect-8tb(hourly), pipeline-gc(daily)

Laptop: vpn-watchdog(60s), seed-finder(10m), cleanup-completed(5m),
        healer-check(5m), healer-backup(daily)
```

## Language
- Default: English for all media
- Anime/Foreign: Dual audio (English + Original) preferred

## NEVER DO
- Mount Samsung 970 EVO Plus NVMe
- Enable laptop WiFi
- Run qBit or gluetun on server
- Put Plex metadata on NTFS
- Allow qBit local disk downloads (set save path to /config/Downloads)
  July 2026: 179GB stuck, laptop /home at 98%. Guard: guard-local-downloads.timer
- Worry about protect-* disabling drives — Plex reads filesystem directly, unaffected
- balance-8tb is DISABLED (was moving media off 8TB to 20TB — backwards)

## Current Counts
```
Plex:      517 movies, 468 shows
Radarr:    1,931 movies (124 downloaded)
Sonarr:    200 shows (53 with episodes)
qBit:      ~1,100 torrents, ~13 active DL, ~2 MB/s
VPN:       AirVPN Toronto
20TB:      60% (7.5TB free)
8TB:       91% (744GB free)
Health:    59/100 overall
```
