# Pipeline-Doc — SERVICES

## Docker Containers (Server)
```
NAME          IMAGE                                    PORT      STATUS
tdarr         ghcr.io/haveagitgat/tdarr:latest         8265-6    Up
decluttarr    ghcr.io/manimatter/decluttarr:latest     —         Up
radarr        lscr.io/linuxserver/radarr:latest        7878      Up
sonarr        lscr.io/linuxserver/sonarr:latest        8989      Up
flaresolverr  ghcr.io/flaresolverr/flaresolverr:latest 8191      Up
autobrr       ghcr.io/autobrr/autobrr                  7474      Up
overseerr     lscr.io/linuxserver/overseerr:latest     5055      Up
bazarr        lscr.io/linuxserver/bazarr:latest        6767      Up
cross-seed    ghcr.io/cross-seed/cross-seed:latest     2468      Up
prowlarr      lscr.io/linuxserver/prowlarr:latest      9696      Up
```

## Docker Containers (Laptop)
```
NAME          IMAGE                                    PORT      STATUS
gluetun       qmcgaw/gluetun:latest                    8080,51413 Up
qbittorrent   lscr.io/linuxserver/qbittorrent:4.6.3    —         Up
  (network_mode: service:gluetun)
  (CPU:2 core, RAM:3GB limit, vol:/mnt/server/downloads:/downloads)
```

## Quality Profiles
### Radarr — HD-720p/1080p (ID=6) [ACTIVE]
- Upgrades: YES, Cutoff: Bluray-1080p
- Allowed: HDTV-720p, WEB-720p, Bluray-720p, HDTV-1080p, WEB-1080p, Bluray-1080p

### Sonarr — HD-720p (ID=3) [ACTIVE]  
- Upgrades: YES, Cutoff: Bluray-720p
- Allowed: HDTV-720p, WEB-720p, Bluray-720p

## Download Client (Radarr + Sonarr)
- Type: qBittorrent, Host: <laptop-ip>:8080
- removeCompleted: TRUE, removeFailed: TRUE
- Category: radar / sonarr
- Language: English default

## Remote Path Mapping
```
<laptop-ip>: /downloads/ → /mnt/20TB/homelab/media/downloads/
```

## Root Folders
```
Radarr: /mnt/20TB/Movies 1 (7.5TB), /mnt/20TB/Movies 4, /mnt/8TB/Movies 2 (744GB)
Sonarr: /mnt/20TB/TV Shows 1 (7.5TB), /mnt/8TB/TV Shows 2 (744GB)
```

## qBittorrent Tuning
```
Active DL:22  Max Torrents:650  Active UL:22
Cache:2048MB  Disk Queue:32MB   Connections:5000/500
Port:51413    Encryption:req    Prealloc:ON
DHT/PEX/LSD:ON  Queueing:ON    AnnAll:ON
```

## Plex
```
Metadata: /var/lib/plex (SSD ext4)
Transcode: /tmp (RAM, 7.8GB), ThrottleBuffer: 1200s, Preset: veryfast
GPU: RTX 3090 Ti NVENC, Remote: port 32400, PlexHome: OFF
Libraries: Movies (523), TV Shows (468), Agent: Plex modern
```

## Language Policy
```
Default: English for all media
Anime/Foreign: Dual audio (English + Original) preferred
```
