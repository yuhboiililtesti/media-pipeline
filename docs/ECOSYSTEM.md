# ECOSYSTEM — Full Homelab Architecture
# Updated: 2026-07-14 — Pipeline v7.1

---

## NETWORK TOPOLOGY

```
ROUTER 10.0.0.1 (XFINITY)
Subnet: 10.0.0.0/24
DNS: 1.1.1.1, 8.8.8.8

┌─────────────────────────────────────────────────────────────┐
│                    10.0.0.0/24 LAN                          │
│                                                             │
│  Ubuntu 24.04 LTS         Ubuntu Server                     │
│  RTX 3090 Ti + GTX 1660S  Dual-core, 3.7GB RAM             │
│  SSH: 2223                SSH: 2224                         │
│  NIC: enp10s0             NIC: enp8s0 (eth ONLY)            │
│                                                             │
│  DESKTOP 10.0.0.234                                        │
└─────────────────────────────────────────────────────────────┘

VPN: AirVPN WireGuard
  Server:  173.249.217.19 (NYC endpoint)
```

---

## SERVER INTERNAL ARCHITECTURE

```
┌──────────────────────────────────────────────────────────┐
│  HOST: Ubuntu 24.04 LTS                                  │
│  AMD Ryzen 7 5800X (8C/16T), 31GB DDR4-3200             │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  DOCKER (16 containers)                          │    │
│  │                                                  │    │
│  │  NETWORK: gluetun-overflow (VPN)                 │    │
│  │    └── qbittorrent-overflow (downloads)          │    │
│  │                                                  │    │
│  │  NETWORK: bridge (media-net)                     │    │
│  │    ├── prowlarr (9696) — indexer hub             │    │
│  │    ├── radarr (7878) — movies                    │    │
│  │    ├── sonarr (8989) — TV shows                  │    │
│  │    ├── bazarr (6767) — subtitles                 │    │
│  │    ├── overseerr (5055) — requests               │    │
│  │    ├── autobrr (7474) — IRC announce             │    │
│  │    ├── flaresolverr (8191) — Cloudflare          │    │
│  │    ├── decluttarr — torrent cleanup              │    │
│  │    ├── tdarr (8265) — HEVC transcode             │    │
│  │    ├── tdarr-node (8266) — transcode worker      │    │
│  │    ├── cross-seed (2468) — cross-seeding         │    │
│  │    ├── immich-server (2283) — photos             │    │
│  │    ├── immich-postgres — immich DB               │    │
│  │    └── immich-redis — immich cache               │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  SYSTEMD SERVICES                               │    │
│  │    plexmediaserver (32400) — media server        │    │
│  │    smbd/nmbd — Samba file sharing                │    │
│  │    fix-nftables.service — firewall persistence   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  PIPELINE SCRIPTS (/opt/)                       │    │
│  │    autonomous-pipeline.py v7.1 (every 10m)      │    │
│  │    anti-seed.py v2 (every 2m)                    │    │
│  │    batch_import.py v3 (every 30m)                │    │
│  │    health-monitor.py (every 5m)                  │    │
│  │    dedupe_media.py (daily)                       │    │
│  │    recovery.py (daily)                           │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  STORAGE                                        │    │
│  │    /mnt/20TB — Movies 1, TV Shows 1, homelab    │    │
│  │    /mnt/8TB — Movies 2, TV Shows 2, docker-data │    │
│  │    / — OS + Plex metadata                        │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

## DATA FLOW

```
1. REQUEST
   User -> Overseerr -> Radarr/Sonarr -> Prowlarr

2. SEARCH
   Prowlarr -> 13 indexers + FlareSolverr -> release found

3. DOWNLOAD
   Radarr/Sonarr -> qBit category (radarr/sonarr) -> qBit starts download
   (via gluetun VPN tunnel, 173.249.217.19 NYC)

4. IMPORT
   autonomous-pipeline.py (every 10m):
     Detects completed downloads in /downloads
     Hardlinks to correct media dir (TV or Movies)
     Triggers Radarr/Sonarr rename + Plex scan

   batch_import.py (every 30m):
     Scans /downloads for completed folders
     Detects TV vs movies (robust regex)
     Cross-type dedup (catches misclassified content)
     Moves to media dir (8TB or 20TB based on free space)
     Triggers Plex rescan

5. ORGANIZE
   Radarr/Sonarr renames files per naming conventions
   Bazarr downloads subtitles
   tdarr transcodes to HEVC (midnight-10am)

6. SERVE
   Plex serves media to clients

7. MAINTAIN
   anti-seed.py (every 2m): cleans dead torrents
   health-monitor.py (every 5m): auto-restarts failed containers
   dedupe_media.py (daily): cross-drive deduplication
   recovery.py (daily): disk vs library audit
```

---


```
HOST (Ubuntu 24.04)
         ├── CPU: 8 vCPUs pinned to cores 8-15
         ├── RAM: 12GB
         ├── Display: QXL fallback
         └── Network: via host NAT

BOOT CHAIN:
     b. virsh net-start default

CLIENT:
```

---

## FILE ORGANIZATION

```
/mnt/20TB/
├── Movies 1/                    234 items — primary movies
├── TV Shows 1/                  54 items — primary TV
├── recycle/                     7-day cleanup
└── homelab/
    ├── media/
    │   ├── downloads/           1384 items — active downloads
    │   ├── Pipeline/
    │   │   └── Pipeline-Doc/    This documentation
    │   └── compose/             Docker compose + configs
    │       ├── docker-compose.yml
    │       ├── .env             WireGuard keys (perms 600)
    │       ├── config.env       Ports, paths, drives
    │       ├── qbittorrent-overflow/
    │       ├── prowlarr/
    │       ├── radarr/
    │       ├── sonarr/
    │       ├── bazarr/
    │       ├── overseerr/
    │       ├── autobrr/
    │       ├── flaresolverr/
    │       ├── tdarr/
    │       ├── cross-seed/config/config.js
    │       ├── decluttarr/config.yaml
    │       └── immich-server/
    └── backup/                  Config backups

/mnt/8TB/
├── Movies 2/                    1476 items — secondary movies
├── TV Shows 2/                  158 items — secondary TV
└── docker-data/                 Docker data-root

/mnt/nvme/
└── pipeline-logs/
    ├── pipeline.log
    ├── import.log
    ├── pipeline_state.json
    ├── import_state.json
    ├── dupe_state.json
    └── recovery_state.json

/opt/
├── autonomous-pipeline.py       v7.1 master controller
├── anti-seed.py                 v2: dead/zero-seed cleanup
├── batch_import.py              v3: correct sorting + dedup
├── health-monitor.py            Container health check
├── dedupe_media.py              Cross-drive deduplication
├── recovery.py                  Disk vs library audit
├── server-health-scan.sh        Full health check
└── backup-configs.sh            Config backup

/etc/pipeline/
└── config.json                  All API keys, tokens, paths (perms 600)

/etc/systemd/system/
├── anti-seed.{service,timer}
├── autonomous-pipeline.{service,timer}
├── batch-import.{service,timer}
├── health-monitor.{service,timer}
├── recovery-sync.{service,timer}
├── media-dedupe.{service,timer}
├── fix-nftables.service
├── plexmediaserver.service
├── samba.service
├── sshd.service
├── nftables.service → /dev/null (masked)
├── transmission-daemon.service (masked)
├── fwupd.service (masked)
└── fwupd-refresh.service (masked)
```

---

## CREDENTIALS MATRIX

| System    | User    | Password        | SSH Port | Notes                    |
|-----------|---------|-----------------|----------|--------------------------|
| Server    | topaz   | USER_PASSWORD  | 2223     | Key-based auth only      |
| Laptop    | topaz   | USER_PASSWORD  | 2224     | Key-based auth           |
| Samba     | topaz   | USER_PASSWORD  | -        | All 4 shares             |
| qBit      | topaz   | USER_PASSWORD  | -        | WebUI + API              |
| VPN       | AirVPN  | (WireGuard key) | -        | Keys in .env, perms 600  |

---

## PORT MAP (Server)

| Port  | Protocol | Service              | Binding        |
|-------|----------|----------------------|----------------|
| 22    | TCP      | SSH (default)        | 0.0.0.0        |
| 2223  | TCP      | SSH (custom)         | 0.0.0.0        |
| 139   | TCP      | NetBIOS              | 0.0.0.0        |
| 137   | UDP      | NetBIOS              | 0.0.0.0        |
| 138   | UDP      | NetBIOS              | 0.0.0.0        |
| 445   | TCP      | SMB                  | 0.0.0.0        |
| 32400 | TCP      | Plex                 | 0.0.0.0        |
| 7474  | TCP      | Autobrr              | 0.0.0.0        |
| 7878  | TCP      | Radarr               | 0.0.0.0        |
| 8083  | TCP      | qBit WebUI           | 0.0.0.0        |
| 8191  | TCP      | FlareSolverr         | 127.0.0.1 only |
| 8265  | TCP      | Tdarr Server         | 0.0.0.0        |
| 8266  | TCP      | Tdarr Node           | 0.0.0.0        |
| 8989  | TCP      | Sonarr               | 0.0.0.0        |
| 9696  | TCP      | Prowlarr             | 0.0.0.0        |
| 5055  | TCP      | Overseerr            | 0.0.0.0        |
| 51414 | TCP+UDP  | qBit Torrent         | 0.0.0.0        |
| 6767  | TCP      | Bazarr               | 0.0.0.0        |
| 2283  | TCP      | Immich               | 0.0.0.0        |
| 2468  | TCP      | Cross-seed           | 0.0.0.0        |
| 4330  | TCP      | Libvirt              | 0.0.0.0        |
| 9090  | TCP      | Libvirt guest        | 0.0.0.0        |
| 44321 | TCP      | Libvirt metrics      | 0.0.0.0        |
| 44322 | TCP      | Libvirt metrics      | 0.0.0.0        |
| 44323 | TCP      | Libvirt metrics      | 0.0.0.0        |

---

## API KEYS

| Service   | Key                                    |
|-----------|----------------------------------------|
| Radarr    | RADARR_API_KEY       |
| Sonarr    | SONARR_API_KEY       |
| Prowlarr  | PROWLARR_API_KEY       |
| Plex      | PLEX_TOKEN                   |
| Discord   | MTQ4OTgzNjM3MDkwMTA3ODE2OA...          |

---

## MONITORING

| Tool        | Location               | What It Monitors                    |
|-------------|------------------------|--------------------------------------|
| Uptime Kuma | laptop:3001            | Server services, port checks         |
| Heimdall    | laptop:8080            | Dashboard for all services           |
| health-monitor.py | Server (every 5m) | Docker container health              |
| fix-nftables.service | Server (boot) | Firewall rules persistence           |

---

## VPN CONFIGURATION

### Server (AirVPN WireGuard)
- Endpoint: 198.44.136.238:1637 (NYC)
- VPN IP: 10.147.17.165/32
- Public IP: 173.249.217.19
- DNS: 1.1.1.1 (configured in gluetun)
- Keys: stored in /mnt/20TB/homelab/media/compose/.env (perms 600)

- Separate VPN instance (not routing through server)
- Used for personal browsing
