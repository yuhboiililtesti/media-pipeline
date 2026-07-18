# Media Pipeline Documentation

## Overview

End-to-end media acquisition, processing, and serving pipeline across the Topaz server.

---

## Download Flow

```
┌──────────┐    ┌──────────┐    ┌────────────┐    ┌───────────────┐
│ autobrr  │───▶│ Prowlarr │───▶│ qBittorrent│───▶│ Sonarr/Radarr │
│ (IRC)    │    │ (indexer)│    │ (download) │    │ (import)      │
└──────────┘    └──────────┘    └─────┬──────┘    └───────┬───────┘
                                      │                    │
                     ┌────────────────┘                    │
                     ▼                                     ▼
              ┌──────────────┐                    ┌───────────────┐
              │ anti-seed    │                    │ Tdarr         │
              │ decluttarr   │                    │ (transcode)   │
              │ (prune)      │                    └───────┬───────┘
              └──────────────┘                            │
                                                          ▼
                                                   ┌──────────────┐
                                                   │ Plex Serve   │
                                                   └──────────────┘
```

### Step-by-Step

| Stage | Tool           | Action                                               |
|-------|----------------|------------------------------------------------------|
| 1     | **autobrr**    | Monitors IRC announce channels, matches filters      |
| 2     | **Prowlarr**   | Searches indexers (TorrentLeech, IPT, etc.)          |
| 3     | **qBittorrent**| Downloads .torrent through gluetun VPN tunnel        |
| 4     | **Sonarr**     | Monitors TV downloads, renames, hardlinks to library |
| 5     | **Radarr**     | Monitors movie downloads, renames, hardlinks         |
| 6     | **Tdarr**      | Transcodes completed media to H.265 (NVENC)          |
| 7     | **Plex**       | Serves the final library to clients                  |

---

## qBittorrent Configuration

### Docker Compose (excerpt)

```yaml
qbittorrent:
  image: lscr.io/linuxserver/qbittorrent:latest
  container_name: qbittorrent
  network_mode: service:gluetun-overflow
  environment:
    - PUID=1000
    - PGID=1000
    - WEBUI_PORT=8083
  volumes:
    - /opt/qbittorrent:/config
    - /mnt/20TB/downloads:/downloads
  restart: unless-stopped
```

### Connection Details

| Parameter        | Value                          |
|------------------|--------------------------------|
| **Network Mode** | `service:gluetun-overflow`     |
| **WebUI Port**   | 8083                           |
| **Username**     | `topaz`                        |
| **Password**     | `USER_PASSWORD`               |
| **API**          | `http://localhost:8083/api/v2` |

### Categories

| Category   | Save Path                          | Managed By |
|------------|------------------------------------|------------|
| `radarr`   | `/mnt/20TB/downloads/radarr`       | Radarr     |
| `sonarr`   | `/mnt/20TB/downloads/sonarr`       | Sonarr     |

### Torrent Management

| Tool          | Function                                  | Interval |
|---------------|-------------------------------------------|----------|
| **anti-seed** | Removes torrents exceeding ratio targets  | Every 2m |
| **decluttarr**| Removes stalled/failed/slow downloads     | Every 60s |

---

## Storage Paths

### /mnt/20TB (Media Array — BTRFS RAID1)

```
/mnt/20TB/
├── downloads/               # qBittorrent active downloads
│   ├── radarr/             # Movie downloads
│   └── sonarr/             # TV downloads
├── media/                   # Plex library root
│   ├── movies/             # Final movie files (hardlinked)
│   └── tv/                 # Final TV files (hardlinked)
├── transcode_cache/        # Tdarr temporary transcode working dir
├── tdarr/                   # Tdarr config (staging from NVMe)
├── backups/                 # Configuration backups
│   ├── docker/
│   ├── sonarr/
│   ├── radarr/
│   └── plex/
├── torrents/                # .torrent files (qBit watch dir)
└── usenet/                  # NZB completion dir (legacy/unused)
```

### /mnt/8TB (Scratch / Overflow)

```
/mnt/8TB/
├── isos/                    # OS ISO images
├── vm-images/               # Raw VM disk images (backups)
└── tmp/                     # General temporary storage
```

### /mnt/nvme (SSD — Fast Storage)

```
/mnt/nvme/
├── docker/                  # Docker root dir (containers, volumes)
├── tdarr/                   # Tdarr database, plugins, cache
├── appdata/                 # Application data
│   ├── plex/               # Plex metadata, thumbnails, DB
│   ├── sonarr/
│   ├── radarr/
│   ├── prowlarr/
│   └── bazarr/
├── vm/                      # Libvirt VM images (active)
│   └── gaming-vm.qcow2     # Windows 11 gaming VM disk
└── transcode_cache/        # Hot Tdarr transcode staging (fast)
```

### Mount Table

| Mountpoint               | Device/FS       | Type    | Purpose                       |
|---------------------------|-----------------|---------|-------------------------------|
| `/mnt/20TB`               | BTRFS RAID1     | HDD     | Primary media + downloads     |
| `/mnt/8TB`                | EXT4            | HDD     | Scratch / bulk storage        |
| `/mnt/nvme`               | EXT4            | NVMe SSD| Docker, VMs, appdata          |

---

## Tdarr Flow

### Libraries

| Library ID | Name            | Source Path              | Output Path         | Status   |
|------------|-----------------|--------------------------|---------------------|----------|
| 1          | Movies (H.265)  | `/mnt/20TB/media/movies` | (same, in-place)    | Active   |
| 2          | TV (H.265)      | `/mnt/20TB/media/tv`     | (same, in-place)    | Active   |
| 3          | Movies (Clean)  | `/mnt/20TB/media/movies` | `/mnt/20TB/media/movies` | Active   |
| 4          | TV (Clean)      | `/mnt/20TB/media/tv`     | `/mnt/20TB/media/tv`     | Active   |

### Plugin Stack (NVENC H.265)

```
Plugin Order:
  1. Tdarr_Plugin_MC93_Migz1FFMPEG
  2. Tdarr_Plugin_MC93_Migz3CleanAudio
  3. Tdarr_Plugin_MC93_Migz4CleanSubs
  4. Tdarr_Plugin_MC93_Migz5Boost
```

#### Plugin 1: Migz1FFMPEG (Transcode)

```json
{
  "container": "mkv",
  "encoder": "hevc_nvenc",
  "force_conform": false,
  "enable_10bit": true,
  "bitrate_cutoff": 20000,
  "target_codec": "hevc",
  "target_bitrate_multiplier": 0.75
}
```

#### Plugin 2: Migz3CleanAudio

```json
{
  "language": "eng",
  "keep_original_lang": true,
  "remove_commentary": true
}
```

#### Plugin 3: Migz4CleanSubs

```json
{
  "language": "eng",
  "keep_original_lang": true,
  "remove_sdh": true
}
```

#### Plugin 4: Migz5Boost

```json
{
  "boost_ac3": false,
  "boost_dts": false,
  "boost_all": false
}
```

### Hardware

| Component      | Detail                       |
|----------------|------------------------------|
| **GPU**        | NVIDIA RTX 3090 Ti (24 GB)   |
| **Encoder**    | NVENC (hevc_nvenc)           |
| **Node CPU**   | Host CPU (all cores)         |
| **Temp Cache** | `/mnt/nvme/transcode_cache`  |

### Worker Limits

| Parameter         | Value |
|-------------------|-------|
| CPU Transcode     | 0     |
| GPU Transcode     | 2     |
| Health Check      | 2     |

---

## API Keys

### Service API Keys

| Service       | URL / Endpoint                         | API Key                             |
|---------------|----------------------------------------|-------------------------------------|
| **Radarr**    | `http://172.20.0.7:7878/api/v3`        | `RADARR_API_KEY` |
| **Sonarr**    | `http://172.20.0.5:8989/api/v3`        | `SONARR_API_KEY` |
| **Prowlarr**  | `http://172.20.0.3:9696/api/v1`        | `7a3f8e2d1c4b5a6f9e8d7c6b5a4f3e2d` |
| **Bazarr**    | `http://172.20.0.8:6767/api`           | `2d4f6a8e0c1b3d5f7a9e8b7c6d5f4a3e` |
| **qBittorrent**| `http://localhost:8083/api/v2`         | (Cookie-based auth)                 |
| **Tdarr**     | `http://172.20.0.10:8265/api/v2`       | `9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c` |
| **Plex**      | `http://localhost:32400`               | `P1x-T0k3n-PL3x-T0k3n-Ex4mpl3`      |
| **autobrr**   | `http://172.20.0.4:7474/api`           | `f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9` |
| **Decluttarr**| `http://172.20.0.6:3000`               | (Internal only)                     |
| **Uptime Kuma**| `http://localhost:3001`               | `kum4-up-t1me-t0ken-pl4ceh0lder`    |

### qBittorrent Login

| Field    | Value            |
|----------|------------------|
| Username | `topaz`          |
| Password | `USER_PASSWORD` |

---

## Monitoring

### Uptime Kuma Checks

| Monitor Name          | Type       | Target                          | Interval |
|-----------------------|------------|---------------------------------|----------|
| Plex Server           | HTTP       | `http://localhost:32400/web`    | 60s      |
| Sonarr                | HTTP       | `http://172.20.0.5:8989`        | 60s      |
| Radarr                | HTTP       | `http://172.20.0.7:7878`        | 60s      |
| qBittorrent WebUI     | HTTP       | `http://localhost:8083`         | 60s      |
| Tdarr                 | HTTP       | `http://172.20.0.10:8265`       | 60s      |
| Prowlarr              | HTTP       | `http://172.20.0.3:9696`        | 60s      |
| Bazarr                | HTTP       | `http://172.20.0.8:6767`        | 60s      |
| Gaming VM (ping)      | Ping       | `192.168.122.x` (dynamic)       | 30s      |
| WAN Connectivity      | Ping       | `1.1.1.1`                       | 30s      |
| gluetun VPN           | HTTP       | `http://localhost:8000`         | 60s      |
| Decluttarr            | HTTP       | `http://172.20.0.6:3000`        | 60s      |
| autobrr               | HTTP       | `http://172.20.0.4:7474`        | 60s      |

### Health Scan Script

```bash
#!/bin/bash
# /opt/media-health.sh
# Comprehensive health check for the media pipeline

echo "=== Media Pipeline Health ==="

# Docker containers
echo -e "\n--- Docker Containers ---"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "plex|sonarr|radarr|prowlarr|qbittorrent|tdarr|bazarr|decluttarr|autobrr|gluetun"

# API health checks
echo -e "\n--- API Health ---"
for svc in "sonarr:8989" "radarr:7878" "prowlarr:9696" "tdarr:8265" "bazarr:6767"; do
    NAME="${svc%%:*}"
    PORT="${svc##*:}"
    CODE=$(curl -so /dev/null -w "%{http_code}" "http://localhost:${PORT}" 2>/dev/null)
    echo "${NAME}: HTTP ${CODE}"
done

# qBit transfer info
echo -e "\n--- qBittorrent Transfer Info ---"
curl -s "http://localhost:8083/api/v2/transfer/info" \
    --cookie "SID=$(curl -s -c - 'http://localhost:8083/api/v2/auth/login' \
    --data 'username=topaz&password=USER_PASSWORD' | grep SID | awk '{print $NF}')" | python3 -m json.tool

# Disk usage
echo -e "\n--- Disk Usage ---"
df -h /mnt/20TB /mnt/8TB /mnt/nvme
```

### qBit API Transfer Info

```bash
# Quick transfer status check
curl -s "http://localhost:8083/api/v2/transfer/info" --cookie "SID=$SID" | python3 -m json.tool
```

Example response:

```json
{
  "dl_info_speed": 52428800,
  "dl_info_data": 1234567890123,
  "up_info_speed": 10485760,
  "up_info_data": 987654321098,
  "dl_rate_limit": 0,
  "up_rate_limit": 0,
  "dht_nodes": 342,
  "connection_status": "connected"
}
```

### Cron Health Reporting

```cron
# Daily pipeline health report
0 8 * * * /opt/media-health.sh | mail -s "Daily Media Health" root

# Hourly disk check
0 * * * * df -h /mnt/20TB /mnt/nvme | grep -E "Use%|[0-9]%" >> /var/log/disk-usage.log
```

---

## Hardlink Architecture

```
qBittorrent downloads to:     /mnt/20TB/downloads/{radarr,sonarr}/
Sonarr/Radarr import via:     Hardlink (same filesystem)
Final library location:       /mnt/20TB/media/{movies,tv}/
Tdarr transcodes in-place:    /mnt/20TB/media/{movies,tv}/ (overwrites)
Plex scans + serves:          /mnt/20TB/media/{movies,tv}/

Hardlink advantage: Zero additional disk space per import.
                   Both download and library paths must be on same filesystem (BTRFS RAID1).
```

### Filesystem Layout

```
/mnt/20TB/                          ← Single BTRFS filesystem
├── downloads/
│   ├── radarr/
│   │   └── Movie.Name.2024.2160p/  ← qBit writes here
│   │       └── movie.mkv           ← inode #1234
│   └── sonarr/
│       └── Show.Name.S01E01/       ← qBit writes here
│           └── episode.mkv         ← inode #5678
└── media/
    ├── movies/
    │   └── Movie Name (2024)/
    │       └── movie.mkv           ← hardlink to inode #1234
    └── tv/
        └── Show Name/
            └── Season 01/
                └── episode.mkv     ← hardlink to inode #5678
```
