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
  │   │   ├── 8 vCPUs (cores 8-15), 12GB RAM, 550GB QCOW2
  │   │   ├── GTX 1660 SUPER (vfio-pci: 0b:00.0-3)
  │   └── virbr0: 192.168.122.0/24 (DHCP, NAT to enp8s0)
```


```
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
```

| Core Range | Count | Assignment               |
|------------|-------|--------------------------|
| 0-5        | 6     | Host OS + Docker         |
| 6-7        | 2     | Reserved (buffer)        |

GRUB configuration:

```
isolcpus=6-15 hugepages=3072
```


```
```

|------------------|-----------|--------------|------------------------------|-----------------------|


|--------------|--------------------|
| GTX 1660 S   | 0b:00.0, 0b:00.1, 0b:00.2, 0b:00.3 |

## Storage Layout

```
/mnt/20TB (20TB): Movies 1, TV Shows 1, downloads, Docker configs, Tdarr, Immich
/mnt/8TB (8TB):   Movies 2, TV Shows 2, Docker overlay2 data
```

| Mount       | Size  | Contents                                                  |
|-------------|-------|-----------------------------------------------------------|
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


| Setting          | Value                              |
|------------------|------------------------------------|
| vCPUs            | 8 (cores 8-15, pinned 1:1)         |
| RAM              | 12GB                               |
| Disk             | 550GB QCOW2 on /mnt/nvme           |
| Network          | virbr0 NAT, port 2225 forwarded    |
