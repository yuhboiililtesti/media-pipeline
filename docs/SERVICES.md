# SERVICES — Complete Docker + System Reference
# Updated: 2026-07-14 — Pipeline v7.1

---

## DOCKER CONTAINERS (16)

### gluetun-overflow
- Image: qmcgaw/gluetun:latest
- Purpose: AirVPN WireGuard tunnel for qBit
- Ports: 8083 (qBit WebUI), 51414 (torrent), 1080, 8000, 8388, 8888
- Network: bridge (published)
- Healthcheck: 30s interval, 10s timeout, 5 retries, 60s start period
- Config: WireGuard keys from .env

### qbittorrent-overflow
- Image: linuxserver/qbittorrent:4.6.3
- Purpose: Primary torrent downloader
- Network: service:gluetun-overflow (shares VPN)
- Volumes: ./qbittorrent-overflow:/config, downloads:/downloads
- Mem limit: 4GB
- Settings: 20 active DL, 200 max torrents, 5000 conn, DHT/PeX/LSD on
- Categories: sonarr, radarr
- Depends on: gluetun-overflow (healthy)

### prowlarr
- Image: linuxserver/prowlarr:latest
- Purpose: Indexer hub — manages all torrent indexers
- Port: 9696
- Mem limit: 1g
- Indexers: 13 (via Torznab API)
- Features: fullSync to Sonarr + Radarr
- API Key: PROWLARR_API_KEY

### radarr
- Image: linuxserver/radarr:latest
- Purpose: Movie management and download automation
- Port: 7878
- Mem limit: 1g
- Quality: HD-720p/1080p (profile ID:6), upgradeAllowed=True
- Root folders: /mnt/20TB/Movies 1, /mnt/8TB/Movies 2
- 2174 monitored movies
- API Key: RADARR_API_KEY

### sonarr
- Image: linuxserver/sonarr:latest
- Purpose: TV show management and download automation
- Port: 8989
- Mem limit: 2g
- Quality: HD-720p (profile ID:3), upgradeAllowed=True, cutoff Bluray-1080p
- Root folders: /mnt/20TB/TV Shows 1, /mnt/8TB/TV Shows 2
- 462 monitored series
- API Key: SONARR_API_KEY

### bazarr
- Image: linuxserver/bazarr:latest
- Purpose: Subtitle management
- Port: 6767
- Connected to: Sonarr + Radarr

### overseerr
- Image: linuxserver/overseerr:latest
- Purpose: Media requests (like Ombi)
- Port: 5055
- Connected to: Plex (http://localhost:32400, token: PLEX_TOKEN)

### autobrr
- Image: ghcr.io/autobrr/autobrr:latest
- Purpose: IRC announce monitoring (private tracker auto-join)
- Port: 7474

### flaresolverr
- Image: ghcr.io/flaresolverr/flaresolverr:latest
- Purpose: Cloudflare protection bypass
- Port: 8191 (bound to 127.0.0.1 only)
- Used by: Prowlarr

### decluttarr
- Image: manimatter/decluttarr:latest
- Purpose: Automatic torrent cleanup
- Mem limit: 256MB
- Config: /mnt/20TB/homelab/media/compose/decluttarr/config.yaml
- Jobs: remove_bad_files, remove_done_seeding, remove_failed_downloads,
  remove_failed_imports, remove_stalled (all enabled)
- Log level: VERBOSE
- qBit name: qBit-Overflow

### tdarr
- Image: ghcr.io/haveagitgat/tdarr:latest
- Purpose: HEVC NVENC transcoding
- Ports: 8265 (server), 8266 (node), 8267
- Mem limit: 2g
- GPU: RTX 3090 Ti NVENC

### tdarr-node
- Image: ghcr.io/haveagitgat/tdarr_node:latest
- Purpose: Tdarr worker node
- Mem limit: 2g

### cross-seed
- Image: ghcr.io/cross-seed/cross-seed:latest
- Purpose: Cross-tracker seeding (finds same torrent on other trackers)
- Port: 2468
- Config: /mnt/20TB/homelab/media/compose/cross-seed/config/config.js
- linkType: symlink (cross-drive compatible)
- matchMode: partial
- action: inject (auto-adds to qBit)
- Indexers: 13 Prowlarr indexers
- Sonarr + Radarr connected

### immich-server
- Image: ghcr.io/immich-app/immich-server:v3.0.1
- Purpose: Photo management (self-hosted Google Photos)
- Port: 2283
- Healthcheck: enabled

### immich-postgres
- Image: pgvector/pgvector:pg14
- Purpose: Immich database
- Mem limit: 1g

### immich-redis
- Image: redis:6.2-alpine
- Purpose: Immich cache
- Mem limit: 512MB

---

## SYSTEM SERVICES

### plexmediaserver
- Port: 32400
- Libraries: Movies (387 items), TV Shows (53 items)
- GPU: RTX 3090 Ti NVENC for hardware transcoding
- Metadata: /var/lib/plex (on SSD)
- Enabled: yes

### smbd / nmbd
- Purpose: Samba file sharing
- Shares: server-20TB, server-8TB, topaz-home, server-root
- Enabled: yes

### libvirtd
- Purpose: KVM/QEMU virtualization for gaming VM
- Enabled: yes (unmasked)

### gaming-vm.service
- Purpose: Autostart gaming VM on boot
- Chain: fix-phantom -> net-start -> start-gaming-vm -> port-fwd
- Enabled: yes

### fix-nftables.service
- Purpose: Rebuild nftables rules on boot (fixes UFW/nftables conflict)
- Type: oneshot (runs once at boot)
- Enabled: yes

### sshd
- Port: 2223 (custom)
- Auth: key-based only (ed25519), password disabled
- Enabled: yes

### unattended-upgrades
- Purpose: Automatic security patches
- Schedule: daily
- Enabled: yes

---

## MASKED/DISABLED SERVICES

| Service              | Why Masked                              |
|----------------------|-----------------------------------------|
| nftables.service     | Conflicts with UFW, can't load xtables  |
| transmission-daemon  | Not used                                |
| fwupd.service        | Not needed                              |
| fwupd-refresh.service| Not needed                              |

---

## DOCKER COMPOSE FILE

Location: /mnt/20TB/homelab/media/compose/docker-compose.yml

Key settings:
- 16 containers total
- gluetun-overflow: WireGuard VPN (keys from .env)
- qbittorrent-overflow: network_mode=service:gluetun-overflow
- radarr/sonarr: mount /mnt/20TB and /mnt/8TB directly
- tdarr: NVIDIA GPU passthrough (NVIDIA_VISIBLE_DEVICES=all)
- All containers: restart unless-stopped
- Media containers have mem_limit set

---

## CONFIG.ENV

Location: /mnt/20TB/homelab/media/compose/config.env

Key variables:
- PUID=1000, PGID=1000, TZ=America/Denver
- SERVERIP=10.0.0.200
- WEBUI_PORT=8083
- Torrent port: 51414
- VPN_DNS=1.1.1.1
- Drives: NVME=/mnt/nvme, HDD1=/mnt/20TB, HDD2=/mnt/8TB
- Downloads: /mnt/20TB/homelab/media/downloads
