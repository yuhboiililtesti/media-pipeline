# CONFIGURATION FILES — Complete Reference

## Server

### Docker Compose
```
/mnt/20TB/homelab/media/compose/docker-compose.yml
  - 10 containers on media-net
  - radarr mounts: /mnt/20TB:/mnt/20TB, /mnt/8TB:/mnt/8TB
  - sonarr mounts: same
  - tdarr: NVIDIA GPU passthrough
  - REMOVED: gluetun, qbittorrent (now on laptop)
```

### Systemd Units
```
/etc/systemd/system/
  torrent-doctor.{service,timer}
  tdarr-post-encode.{service,timer}
  balance-8tb.{service,timer}
  seed-finder.{service,timer}
  health-score.{service,timer}
  disk-space-guard.{service,timer}
  disk-watchdog.{service,timer}
  crash-watchdog.{service,timer}
  completed-import.{service,timer}
  discovery-engine.{service,timer}
  discovery-weekly.{service,timer}
  discovery-monthly.{service,timer}
  discovery-yearly.{service,timer}
  nightly-backup.{service,timer}
  complete-media.{service,timer}
  protect-8tb.{service,timer}
  pipeline-gc.{service,timer}
  smart-fill.{service,timer}
  auto-dedup.{service,timer}
  taste-daily.{service,timer}
  taste-weekly.{service,timer}
  taste-monthly.{service,timer}
  taste-yearly.{service,timer}
  pipeline-dashboard.service

  plexmediaserver.service.d/override.conf   (PlexHome=0 auto-fix)
```

### Fstab
```
UUID=A2DCD02CDCCFF915  /mnt/20TB  ntfs-3g  uid=1000,gid=1000,dmask=000,fmask=000,noatime,nofail  0  0
UUID=A658C85958C829BF  /mnt/8TB   ntfs-3g  uid=1000,gid=1000,dmask=000,fmask=000,noatime,nofail  0  0
# NVMe RETIRED:
#UUID=85b5af87-... /mnt/nvme ext4 defaults,noatime,nofail  0  2
```

### Exports
```
/etc/exports:
  /mnt/20TB/homelab/media/downloads 10.0.0.234(rw,sync,no_subtree_check,all_squash,anonuid=1000,anongid=1000)
```

### UFW
```
Default: deny incoming, allow outgoing
Open: 2223(SSH), 32400(Plex), 111+2049(NFS→10.0.0.234 only), 8090(Dashboard), 137-139+445(SMB)
```

### Plex
```
/var/lib/plex/Plex Media Server/Preferences.xml
  MachineIdentifier: d7ad8e2f2eaca81e3c4e4a887c46ae5a9e2b9270
  TranscoderTempDirectory: /tmp
  TranscoderH264BackgroundPreset: veryfast
  TranscoderThrottleBuffer: 1200
  TranscoderQuality: 1
  PlexOnlineHome: 0 (set via API + ExecStartPost override)
  SecureConnections: 0
```

### Pipeline
```
/mnt/20TB/homelab/media/Pipeline/
  discovery/          v4.0 engine
  safeguards/         rules.json + guard.py
  taste/              per-user profiles
  candidates/         4 queues
  scripts/            17 scripts
  knowledge/          institutional memory
  logs/               unified logging
  state/              HEALTH_SCORE.json, snapshots
  plexlist.txt        3,234 lines
  KNOWN_BAD.md        institutional memory
```

## Laptop

### Docker Compose
```
/home/laptop/pipeline/docker-compose.yml
  gluetun: AirVPN WireGuard, FIREWALL=on, ports 8080+51413
  qbittorrent: network_mode: gluetun, RAM 3.5GB, vol /mnt/server/downloads:/downloads
```

### Systemd Units
```
/etc/systemd/system/
  vpn-watchdog.{service,timer}
  cleanup-completed.{service,timer}
  seed-finder.{service,timer}
  healer-check.{service,timer}
  healer-backup.{service,timer}

  docker.service.d/nfs-wait.conf  (RequiresMountsFor=/mnt/server/downloads)
```

### Fstab
```
10.0.0.201:/mnt/20TB/homelab/media/downloads /mnt/server/downloads nfs4 rw,vers=4.2,soft,timeo=10,retrans=2,async,noatime 0 0
```

### Network
```
/etc/systemd/network/10-ethernet.network
  enp8s0: 10.0.0.234/24 static, gateway 10.0.0.1, DNS 1.1.1.1+8.8.8.8

/etc/systemd/network/99-disable-wifi.network
  wlp5s0: Unmanaged=yes  (WiFi DISABLED+MASKED)
```

### qBittorrent Config
```
/home/laptop/pipeline/config/qbittorrent/qBittorrent/qBittorrent.conf
  Session\DefaultSavePath=/downloads/
  Session\Port=51413
  Session\MaxActiveDownloads=15
  Session\MaxActiveTorrents=200
  WebUI\Password_PBKDF2=<hash>
```

## Desktop

### Pipeline Documentation
```
/home/topaz/home/Pipeline-Doc/
  README.md, MASTER.md, API-REFERENCE.md
  ARCHITECTURE.md, AUTOMATION.md, COMMANDS.md
  HARDWARE.md, NETWORK.md, SERVICES.md
  RECOVERY.md, TASTE.md, DISCOVERY.md
  QBIT.md, TIMERS.md, FLOW.md
  have-list.txt (1,068 lines)
  info (credentials)
```

### SSH Config (~/.ssh/config)
```
Host server
  HostName 10.0.0.201
  Port 2223
  User topaz

Host laptop
  HostName 10.0.0.234
  Port 2225
  User laptop
```
