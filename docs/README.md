# PIPELINE v7.4 — COMPLETE DOCUMENTATION
# Updated: 2026-07-18
# Pipeline version: v7.3 (autonomous-pipeline.py)
# Batch import version: v3 (batch_import.py)
# Deduper version: v2 (hash-verified, Tdarr-safe)
# Classifier version: v1 (classify_media.py)

---

## QUICK REFERENCE

| Service     | URL                          | Port   |
|-------------|------------------------------|--------|
| Plex        | http://10.0.0.200:32400      | 32400  |
| qBit-Overflow | http://10.0.0.200:8083     | 8083   |
| Sonarr      | http://10.0.0.200:8989       | 8989   |
| Radarr      | http://10.0.0.200:7878       | 7878   |
| Prowlarr    | http://10.0.0.200:9696       | 9696   |
| Bazarr      | http://10.0.0.200:6767       | 6767   |
| Overseerr   | http://10.0.0.200:5055       | 5055   |
| Tdarr       | http://10.0.0.200:8265       | 8265   |
| Tdarr Node  | http://10.0.0.200:8266       | 8266   |
| Cross-seed  | http://10.0.0.200:2468       | 2468   |
| Autobrr     | http://10.0.0.200:7474       | 7474   |
| FlareSolverr| http://10.0.0.200:8191       | 8191   |
| Immich      | http://10.0.0.200:2283       | 2283   |

| System      | Address                      | SSH Port |
|-------------|------------------------------|----------|
| Server      | `ssh server` (10.0.0.200)    | 2223     |
| Laptop      | 10.0.0.234                   | 2225     |

---

## SYSTEM INVENTORY

### Server (10.0.0.200)
- **CPU:** AMD Ryzen 7 5800X (8C/16T) @ 3.8-4.6 GHz
- **OS:** Ubuntu 24.04 LTS
- **NIC:** enp10s0 (TCP keepalive: 60s, WoL enabled, power saving disabled)

| Device     | Size   | Mount     | FS   | Model                         | Use% |
|------------|--------|-----------|------|-------------------------------|------|
| /dev/sda   | 120GB  | /         | ext4 | WDC WDS120G2G0A              | OS   |
| /dev/sdb   | 20TB   | /mnt/20TB | ext4 | Seagate Exos ST20000NM007D   | 29%  |
| /dev/sdc   | 8TB    | /mnt/8TB  | ext4 | Seagate ST8000DM004           | 6%   |
| /dev/nvme0n1 | 1.8TB | /mnt/nvme | ext4 | Samsung 970 EVO Plus         | 8%   |

- **CPU:** Dual-core
- **RAM:** 3.7GB
- **OS:** Ubuntu Server
- **Services:** Uptime Kuma (:3001), Heimdall (:8080), health-monitor cron

- **CPU:** AMD Ryzen 5 5500 (12) @ 4.51 GHz
- **RAM:** 15.4GB
- **Disk:** 2x500GB HDDs + 112GB SSD
- **VPN:** AirVPN WireGuard

---

## PIPELINE FLOW v7.1

```
 REQUEST LAYER
 Overseerr(5055) + have-list.txt
         |
         v
  Radarr(7878) + Sonarr(8989)    [462 series / 2174 movies monitored]
         |
         v
  Prowlarr(9696) -> 13 indexers + FlareSolverr(8191)
         |
         v
 DOWNLOAD LAYER
 qBit-Overflow(8083) ----+
  (via gluetun VPN)      |
  (51414 torrent TCP+UDP)|
                         +--> /downloads/
 cross-seed(2468) -------+     |
  (symlink inject)            |
                               v
 IMPORT LAYER                  |
 batch_import.py (every 30min) |  autonomous-pipeline.py (every 10min)
  - TV/movie detection         |   - hardlink to media dirs
  - cross-type dedup           |   - correct sorting
  - size-based dedup           |
         |                     |
         v                     v
 MEDIA LAYER
 /mnt/20TB/Movies 1 (234 items)  |  /mnt/8TB/Movies 2 (1476 items)
 /mnt/20TB/TV Shows 1 (54 items) |  /mnt/8TB/TV Shows 2 (158 items)
         |
         v
 Plex(32400) -> 387 movies, 53 TV shows
         |
         v
 tdarr(8265/8266) -> HEVC NVENC transcode
 Bazarr(6767) -> subtitles
 Decluttarr -> torrent cleanup
 media-dedupe.py (daily) -> cross-drive dedup
```

---

## DOCKER SERVICES (16 containers)

| Container              | Image                                    | Port(s)           | Network           | Mem Limit | Notes                     |
|------------------------|------------------------------------------|-------------------|--------------------|-----------|---------------------------|
| gluetun-overflow       | qmcgaw/gluetun:latest                    | 8083,51414        | bridge (published) | -         | AirVPN WireGuard, healthcheck |
| qbittorrent-overflow   | linuxserver/qbittorrent:4.6.3            | (via gluetun)     | gluetun network   | 4GB       | Downloads, 20 active DL   |
| prowlarr               | linuxserver/prowlarr:latest              | 9696              | bridge            | 1g        | 13 indexers, fullSync     |
| radarr                 | linuxserver/radarr:latest                | 7878              | bridge            | 1g        | Movies, upgradeAllowed    |
| sonarr                 | linuxserver/sonarr:latest                | 8989              | bridge            | 2g        | TV, upgradeAllowed        |
| bazarr                 | linuxserver/bazarr:latest                | 6767              | bridge            | -         | Subtitles                 |
| overseerr              | linuxserver/overseerr:latest             | 5055              | bridge            | -         | Media requests, Plex linked |
| autobrr                | ghcr.io/autobrr/autobrr:latest           | 7474              | bridge            | -         | IRC announce monitoring   |
| flaresolverr           | ghcr.io/flaresolverr/flaresolverr:latest | 8191              | bridge            | -         | Cloudflare bypass, 127.0.0.1 only |
| decluttarr             | manimatter/decluttarr:latest             | (none)            | bridge            | 256MB     | Torrent cleanup, VERBOSE  |
| tdarr                  | ghcr.io/haveagitgat/tdarr:latest         | 8265-8267         | bridge            | 2g        | HEVC NVENC transcode      |
| tdarr-node             | ghcr.io/haveagitgat/tdarr_node:latest    | 8266              | bridge            | 2g        | Tdarr worker node         |
| cross-seed             | ghcr.io/cross-seed/cross-seed:latest     | 2468              | bridge            | -         | Symlink cross-seeding     |
| immich-server          | ghcr.io/immich-app/immich-server:v3.0.1  | 2283              | bridge            | -         | Photo management, healthy |
| immich-postgres        | pgvector/pgvector:pg14                    | 5432 (internal)   | bridge            | 1g        | Immich database           |
| immich-redis           | redis:6.2-alpine                         | 6379 (internal)   | bridge            | 512MB     | Immich cache              |

---

## QBITTORRENT SETTINGS (v7.1)

| Setting                | Value  |
|------------------------|--------|
| max_active_downloads   | 20     |
| max_active_torrents    | 200    |
| max_active_uploads     | 20     |
| max_connec             | 5000   |
| max_connec_per_torrent | 200    |
| up_limit               | 0 (unlimited) |
| dht                    | true   |
| pex                    | true   |
| lsd                    | true   |
| temp_path              | /downloads/incomplete |
| categories             | sonarr, radarr |

---

## QUALITY PROFILES

### Sonarr (TV)
| Profile | Name          | ID  | upgradeAllowed | Cutoff        |
|---------|---------------|-----|----------------|---------------|
| TV      | HD-720p       | 3   | true           | Bluray-1080p  |

### Radarr (Movies)
| Profile | Name              | ID  | upgradeAllowed | Cutoff |
|---------|-------------------|-----|----------------|--------|
| Movies  | HD-720p/1080p     | 6   | true           | HD     |

**NO 4K (2160p) ALLOWED. NO cam/TS rips.**

---

## KEY CREDENTIALS

| Service    | Username | Password / Key                             |
|------------|----------|--------------------------------------------|
| All systems| topaz    | USER_PASSWORD                             |
| Server SSH | topaz    | Key-based (ed25519), password DISABLED     |
| SSH Key    | -        | ~/.ssh/server_ed25519                      |
| Radarr API | -        | RADARR_API_KEY           |
| Sonarr API | -        | SONARR_API_KEY           |
| Prowlarr   | -        | PROWLARR_API_KEY           |
| Plex Token | -        | PLEX_TOKEN                       |
| VPN        | AirVPN   | WireGuard keys in .env (perms 600)         |
| VPN Public | -        | 173.249.217.19 (NYC)                       |

---

## MOUNT PATHS

```
/mnt/20TB/Movies 1        1017 items   Primary movies (20TB Seagate Exos)
/mnt/20TB/TV Shows 1      81 items    Primary TV (20TB Seagate Exos)
/mnt/8TB/Movies 2         1741 items  Secondary movies (8TB Seagate)
/mnt/8TB/TV Shows 2       98 items    Secondary TV (8TB Seagate)
/mnt/20TB/homelab/media/downloads  368 items  Active downloads
```

---

## ACTIVE TIMERS

| Timer                    | Interval  | Script                           | Purpose                              |
|--------------------------|-----------|----------------------------------|--------------------------------------|
| anti-seed.timer          | every 2m  | /opt/anti-seed.py               | Delete dead/zero-seed torrents       |
| autonomous-pipeline.timer| every 10m | /opt/autonomous-pipeline.py     | v7.1 master controller (14 modules)  |
| batch-import.timer       | every 30m | /opt/batch_import.py            | v3: Sort downloads to media dirs     |
| health-monitor.timer     | every 5m  | /opt/health-monitor.py          | Auto-restart failed containers       |
| recovery-sync.timer      | daily     | /opt/recovery.py                | Disk vs Radarr/Sonarr scan           |
| media-dedupe.timer       | daily     | /opt/dedupe_media.py            | Cross-drive deduplication            |

---

## PIPELINE MODULES (autonomous-pipeline.py v7.1)

| # | Module             | What It Does                                           |
|---|--------------------|-------------------------------------------------------|
| 1 | DISK GUARD         | Pause downloads at 98% disk, route to 8TB primary     |
| 2 | QBIT MAX           | Optimize qBit: DHT/PeX/LSD, 5000 conn, unlimited UL  |
| 3 | ANTI-DUPE          | Remove duplicate torrents by hash                      |
| 4 | AUDIO GUARD        | Delete non-English torrents (anime dual-audio kept)    |
| 5 | LEECH CLEANUP      | Delete at 100%, pause active seeders                   |
| 6 | DEAD PATROL        | Remove 0-seed torrents with <5% progress               |
| 7 | AUTO-IMPORT        | Hardlink completed downloads to media dirs (correct sorting) |
| 8 | *ARR TRIGGERS      | RefreshMonitoredDownloads + ProcessMonitoredDownloads + RescanSeries |
| 9 | SMART FILL         | Search when queue <80, MissingMoviesSearch + MissingEpisodeSearch |
| 10| SEASONAL CASCADE   | S01 done -> auto-unlock S02                            |
| 11| PROWLARR SYNC      | fullSync to Radarr + Sonarr                           |
| 12| PLEX SCAN          | Refresh Movies + TV Shows libraries                    |
| 13| DISK PURGE         | Delete non-English files from media dirs               |
| 14| HEALTH CHECK       | Docker auto-restart unhealthy containers               |

---

## BATCH IMPORT (batch_import.py v3)

Runs every 30 minutes via batch-import.timer.

1. Builds file index from all 4 media directories (for dedup)
2. Scans /downloads for completed torrent folders
3. **TV Detection:** Strong regex patterns (SxxExx, Sxx., Season X) with false-positive exclusions
4. **Movie Detection:** Everything not matching TV patterns
5. **Cross-type Dedup:** Checks if movie exists in TV dirs and vice versa
6. **Size-based Dedup:** Catches renames (within 1MB tolerance)
7. Moves to media dir (8TB or 20TB based on free space)
8. Triggers Plex rescan after moves
9. State tracked in /mnt/nvme/pipeline-logs/import_state.json

---

## DEDUP (dedupe_media.py)

Runs daily via media-dedupe.timer.

- Scans all 4 media directories
- Finds duplicates by filename + file size
- **Keeper selection:** Prefers TV Shows dirs over Movies dirs
- Prefers organized subdirectory copies over loose files
- Cross-drive dedup (catches copies across 20TB and 8TB)
- **First run result:** 79 dupes deleted, 132.8 GB recovered
- State: /mnt/nvme/pipeline-logs/dupe_state.json

---

## FIREWALL (nftables + UFW)

UFW is active but nftables does the actual packet filtering (policy DROP).
fix-nftables.service flushes and rebuilds clean rules on boot.

All ports restricted to 10.0.0.0/24 (LAN) except SSH.

**Open TCP ports:** 22, 2223 (SSH), 139, 445 (SMB), 32400 (Plex), 8989 (Sonarr),
7878 (Radarr), 9696 (Prowlarr), 8083 (qBit WebUI), 5055 (Overseerr),
6767 (Bazarr), 8265, 8266 (Tdarr), 7474 (Autobrr), 8191 (FlareSolverr),
51414 (qBit torrent), 2468 (cross-seed), 4330 (Libvirt), 5900 (SPICE),

**Open UDP ports:** 137, 138 (NetBIOS), 51414 (qBit torrent)

---


- **OS:** Windows 11 Pro
- **CPU:** 8 vCPUs pinned to cores 8-15
- **RAM:** 10GB (reduced from 12GB for server stability)
- **Autostart:** Enabled on cold boot

---


- Samba mounts: server-20TB, server-8TB
- VPN: AirVPN WireGuard (separate from server)
