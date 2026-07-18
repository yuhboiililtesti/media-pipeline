# System Architecture

## Network Map

```
Internet → AirVPN (198.44.136.238:1637, WireGuard) → gluetun-overflow (172.20.0.9)
                                                    → qBittorrent (shares gluetun network)
```

### Machines

| Hostname    | IP          | OS              | Hardware                      | Role                    |
|-------------|-------------|-----------------|-------------------------------|-------------------------|
| APOS        | 10.0.0.200  | Ubuntu 24.04    | Ryzen 5800X, 31GB RAM         | Media server + Docker   |
| Cachy       | 10.0.0.192  | CachyOS, KDE 6.7| RTX 3080                      | Moonlight client        |
| Laptop      | 10.0.0.234  | Ubuntu          | ThinkPad SL510                | Monitoring + dashboard  |

### APOS (10.0.0.200) — Ubuntu 24.04, Ryzen 5800X, 31GB RAM

```
10.0.0.200 (APOS) — Ubuntu 24.04, Ryzen 5800X, 31GB RAM
  ├── Docker (media-net: 172.20.0.0/16)
  │   ├── gluetun-overflow (VPN gateway)
  │   ├── qbittorrent-overflow (network_mode: service:gluetun)
  │   ├── sonarr:8989, radarr:7878, prowlarr:9696
  │   ├── bazarr:6767, overseerr:5055
  │   ├── tdarr:8265 (RTX 3090 Ti NVENC), tdarr-node
  │   ├── flaresolverr:8191, autobrr:7474, jackett:9117
  │   ├── decluttarr (cleanup)
  │   └── immich-server:2283, immich-postgres, immich-redis
  ├── Plex:32400 (native, Plex Pass v1.43.3)
  ├── libvirt/KVM
  │   ├── win10-gaming VM (192.168.122.x via virbr0 NAT)
  │   │   ├── 8 vCPUs (cores 8-15), 12GB RAM, 550GB QCOW2
  │   │   ├── GTX 1660 SUPER (vfio-pci: 0b:00.0-3)
  │   │   ├── Sunshine NVENC: 47989-48010
  │   │   └── SSH: 2225 (DNAT forwards to VM)
  │   └── virbr0: 192.168.122.0/24 (DHCP, NAT to enp8s0)
  ├── GPU1: RTX 3090 Ti (host, nvidia driver 580.159.03)
  └── GPU2: GTX 1660 SUPER (vfio-pci, isolated from host)
```

### Cachy (10.0.0.192) — CachyOS, KDE Plasma 6.7, RTX 3080

```
10.0.0.192 (Cachy) — CachyOS, KDE Plasma 6.7, RTX 3080
  └── Moonlight client → streams VM desktop 1080p120
```

### Laptop (10.0.0.234) — Ubuntu, ThinkPad SL510

```
10.0.0.234 (Laptop) — Ubuntu, ThinkPad SL510
  ├── Uptime Kuma:3001 (monitors all services)
  └── Heimdall:8080 (dashboard)
```

## Data Flow

```
1. autobrr monitors IRC → announces new releases
2. prowlarr/jackett search indexers
3. sonarr/radarr grab releases → send to qBittorrent
4. qBittorrent downloads via AirVPN → saves to /mnt/20TB/homelab/media/downloads
5. sonarr/radarr import completed downloads → /mnt/20TB/Movies 1 or TV Shows 1
6. tdarr transcodes to H.265 (RTX 3090 Ti NVENC)
7. Plex serves media to clients
8. decluttarr removes stalled/failed downloads
9. anti-seed clears seeding torrents every 2 minutes
```

### Pipeline Summary

| Step | Service         | Action                           | Target                          |
|------|-----------------|----------------------------------|---------------------------------|
| 1    | autobrr         | Monitor IRC announcements        | n/a                             |
| 2    | prowlarr/jackett| Search indexers                  | n/a                             |
| 3    | sonarr/radarr   | Grab releases                    | qBittorrent                     |
| 4    | qBittorrent     | Download via AirVPN              | /mnt/20TB/homelab/media/downloads|
| 5    | sonarr/radarr   | Import completed downloads       | /mnt/20TB/Movies 1 / TV Shows 1 |
| 6    | tdarr           | Transcode to H.265               | n/a                             |
| 7    | Plex            | Serve media to clients           | n/a                             |
| 8    | decluttarr      | Remove stalled/failed downloads  | n/a                             |
| 9    | anti-seed       | Clear seeding torrents           | every 2 minutes                 |

## CPU Isolation

```
Cores 0-5:  Host OS + Docker pipeline
Cores 6-7:  Reserved (buffer)
Cores 8-15: Windows VM (8 vCPUs pinned 1:1)
```

| Core Range | Count | Assignment               |
|------------|-------|--------------------------|
| 0-5        | 6     | Host OS + Docker         |
| 6-7        | 2     | Reserved (buffer)        |
| 8-15       | 8     | Windows VM (pinned 1:1)  |

GRUB configuration:

```
isolcpus=6-15 hugepages=3072
```

## GPU Allocation

```
RTX 3090 Ti (03:00.0) → Host: nvidia driver 580 → Tdarr NVENC, Plex HW transcode
GTX 1660 SUPER (0b:00.0) → vfio-pci → Windows VM: driver 560.94 → Sunshine NVENC
```

| GPU              | PCI Addr  | Driver       | Consumer                     | Purpose               |
|------------------|-----------|--------------|------------------------------|-----------------------|
| RTX 3090 Ti      | 03:00.0   | nvidia 580   | Host                         | Tdarr NVENC, Plex HW  |
| GTX 1660 SUPER   | 0b:00.0   | vfio-pci     | Windows VM (driver 560.94)   | Sunshine NVENC        |

### GPU Affinity Table

| GPU          | vfio-pci IDs       |
|--------------|--------------------|
| GTX 1660 S   | 0b:00.0, 0b:00.1, 0b:00.2, 0b:00.3 |

## Storage Layout

```
/mnt/nvme (2TB):  VM disk (550GB), Plex data/transcode, Tdarr cache, swap (32GB)
/mnt/20TB (20TB): Movies 1, TV Shows 1, downloads, Docker configs, Tdarr, Immich
/mnt/8TB (8TB):   Movies 2, TV Shows 2, Docker overlay2 data
```

| Mount       | Size  | Contents                                                  |
|-------------|-------|-----------------------------------------------------------|
| /mnt/nvme   | 2TB   | VM QCOW2 (550GB), Plex data/transcode, Tdarr cache, swap (32GB) |
| /mnt/20TB   | 20TB  | Movies 1, TV Shows 1, downloads, Docker configs, Tdarr, Immich |
| /mnt/8TB    | 8TB   | Movies 2, TV Shows 2, Docker overlay2 data                |

## Docker Services

### media-net (172.20.0.0/16)

| Service              | Port  | Notes                            |
|----------------------|-------|----------------------------------|
| gluetun-overflow     | —     | VPN gateway (WireGuard)          |
| qbittorrent-overflow | —     | network_mode: service:gluetun    |
| sonarr               | 8989  | TV show management               |
| radarr               | 7878  | Movie management                 |
| prowlarr             | 9696  | Indexer manager                  |
| bazarr               | 6767  | Subtitle management              |
| overseerr            | 5055  | Media requests                   |
| tdarr                | 8265  | Transcoding (3090 Ti NVENC)      |
| tdarr-node           | —     | Tdarr worker node                |
| flaresolverr         | 8191  | Cloudflare bypass                |
| autobrr              | 7474  | IRC announce monitoring          |
| jackett              | 9117  | Torznab indexer proxy            |
| decluttarr           | —     | Download cleanup                 |
| immich-server        | 2283  | Photo management                 |
| immich-postgres      | —     | Immich database                  |
| immich-redis         | —     | Immich cache                     |

## Native Services (APOS)

| Service | Port   | Version     | Notes                        |
|---------|--------|-------------|------------------------------|
| Plex    | 32400  | 1.43.3      | Plex Pass, native install    |

## VM Configuration (win10-gaming)

| Setting          | Value                              |
|------------------|------------------------------------|
| vCPUs            | 8 (cores 8-15, pinned 1:1)         |
| RAM              | 12GB                               |
| Disk             | 550GB QCOW2 on /mnt/nvme           |
| GPU              | GTX 1660 SUPER (vfio-pci passthrough) |
| GPU Driver       | 560.94                             |
| Network          | virbr0 NAT, port 2225 forwarded    |
| Streaming        | Sunshine NVENC, ports 47989-48010  |
| Client           | Moonlight from Cachy (1080p120)    |
