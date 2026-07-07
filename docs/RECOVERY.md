# Pipeline-Doc — RECOVERY


## DR Test Plan

### Unverified Recovery Procedures
The following have NEVER been fully tested:

| Procedure | Confidence | Risk | Test Plan |
|-----------|-----------|------|-----------|
| Server rebuild | 70% | High | Rebuild on spare machine from MASTER.md |
| Laptop rebuild | 70% | Medium | Rebuild on spare machine |
| Total loss | 10% | Critical | Full rebuild from scratch |

### Recommended DR Test (Annual)
1. Spin up spare machine or VM
2. Follow MASTER.md rebuild steps
3. Restore from latest nightly backup
4. Verify: Plex plays media, Radarr/Sonarr work, qBit downloads
5. Document results in RECOVERY.md with date and outcome

### Last DR Test
Date: NEVER
Result: UNTESTED
Next scheduled: —


## Rebuild Confidence
```
Procedure              Tested  Confidence  Last Test
qBit recovery           YES     100%        2026-06-29
Plex restore            YES      95%        2026-06-29
*arr DB restore         YES      90%        2026-06-30
Nightly backup restore   YES      90%        —
NFS remount              YES     100%        2026-06-30
Server full rebuild     PARTIAL   70%        —
Total loss              NEVER     10%        —
```

## Quick Recovery Commands

### Laptop Dies
```bash
# 1. Any Linux machine with Docker
# 2. Set static IP <laptop-ip>/24
# 3. Restore /home/laptop/pipeline/ from backup
# 4. Mount NFS: <server-ip>:/mnt/20TB/homelab/media/downloads
docker compose up -d
systemctl enable vpn-watchdog cleanup-completed seed-finder healer-check
```

### Server Dies
```bash
# 1. Install Arch Linux
# 2. Install Docker, NFS server, Plex
# 3. Restore fstab, mount drives
# 4. Restore docker-compose.yml
docker compose up -d
systemctl enable --now plexmediaserver
# 5. Restore /etc/exports, apply: exportfs -arv
# 6. Restore systemd timers
# 7. Apply UFW rules
# 8. Restore Radarr/Sonarr/Prowlarr databases from nightly backup
```

### Plex DB Corruption
```bash
systemctl stop plexmediaserver
# Restore from backup:
cp -r /path/to/backup/Plex\ Media\ Server /var/lib/plex/
systemctl start plexmediaserver

# OR: Fresh start with library recreation via API
curl -X POST 'http://localhost:32400/library/sections?name=Movies&type=movie&agent=tv.plex.agents.movie&location=/mnt/20TB/Movies+1...'
```

### 20TB Drive Failure
```bash
# 1. Replace drive
# 2. Format ext4 (preferred) or NTFS
# 3. Mount at /mnt/20TB
# 4. Restore homelab/ from backup
# 5. Radarr/Sonarr will re-download all media (time: days to weeks)
```

### Router Reset
```bash
# 1. Subnet: 10.0.0.0/24
# 2. Reserve: <server-ip> (server), <laptop-ip> (laptop)
# 3. Forward: 32400 TCP → <server-ip>
# 4. Optional: 8090 TCP → <server-ip> (Dashboard)
```

## Nightly Backup — What Gets Saved
```
- Radarr/Sonarr/Prowlarr database backups
- Docker compose files (server + laptop)
- Plex Preferences.xml
- All systemd units (service, timer, mount)
- /etc/fstab, /etc/exports, sshd_config
- UFW rules
- All Pipeline scripts
- qBittorrent config
- Network configs
- SSH config
- Per-user taste profiles
└─ tar archive → /mnt/500gb-1/homelab-backup/archives/ (7 days retained)
```

## Backup Restore
```bash
# Extract latest:
cd /mnt/500gb-1/homelab-backup/archives/
tar xzf homelab-backup-$(date +%Y-%m-%d).tar.gz

# Restore *arr databases:
# Stop container, restore DB files, start container

# Restore Plex:
# Stop Plex, restore /var/lib/plex, start Plex
```
