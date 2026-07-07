# PIPELINE MASTER DOCUMENT — Complete Reconstruction Guide
# If every machine exploded tomorrow, this rebuilds everything.
# Generated: 2026-07-03 | Version: v4.0

---

## 1. MACHINES

### Server (plexy, <server-ip>)
```
CPU: Multi-core x86_64 | GPU: RTX 3090 Ti (NVENC 24GB)
OS: Arch Linux LVM (root 86.8G ext4, home 24G ext4)
NIC: enp6s0f0 | SSH: <user>@<server-ip> -p 2223

DRIVES:
  sda2  18.2TB NTFS /mnt/20TB (64%, 7.5TB free) — media, downloads, Pipeline
  sdc2   7.3TB NTFS /mnt/8TB  (85%, 1.2TB free) — secondary media
  sdb  111.8GB ext4 LVM (/, /home)              — OS, Plex metadata
  nvme0  1.8TB ext4 UNMOUNTED — RETIRED (controller failure)
```

### Laptop (<laptop-ip>)
```
CPU: Dual-core | RAM: 3.7GB | OS: Ubuntu 24.04
Disk: 232.9GB HDD | NIC: enp8s0 static <laptop-ip>/24 (WiFi MASKED)
SSH: laptop@<laptop-ip> -p 2225
qBit: DL:15, Tor:200, Cache:1536MB | gluetun AirVPN Toronto
```

### Desktop (<desktop-ip>)
```
CachyOS | /mnt/500gb-1 — homelab backup target
Pipeline-Doc: /home/topaz/home/Pipeline-Doc/
```

---

## 2. NETWORK

```
Router: <router-ip> (XFINITY) | Subnet: 10.0.0.0/24
Server: <server-ip> | Laptop: <laptop-ip> | Desktop: <desktop-ip>

Port Forwards: 32400 TCP → <server-ip> (Plex)
VPN: AirVPN WireGuard, <vpn-public-ip> (Toronto), endpoint <vpn-public-ip>:1637
     Killswitch: FIREWALL=on, ports: 51413, 8080

UFW (server): deny incoming, allow outgoing
  Open: 2223(SSH), 32400(Plex), 111+2049(NFS→laptop), 8090(Dashboard)
```

---

## 3. STORAGE

```
/mnt/20TB (64%) — Movies 1/4, TV Shows 1, homelab/media/, downloads, Pipeline
/mnt/8TB  (85%) — Movies 2, TV Shows 2 (balancer moves to 20TB at 85%)
/ (75%)         — Plex metadata (/var/lib/plex — MUST be ext4, NEVER NTFS)

NFS: /mnt/20TB/homelab/media/downloads → <laptop-ip> (rw, all_squash anonuid=1000)
Laptop NFS: <server-ip>:/mnt/20TB/homelab/media/downloads → /mnt/server/downloads
```

---

## 4. DOCKER STACK

### Server (10 containers on media-net)
```
radarr:7878        sonarr:8989        prowlarr:9696
bazarr:6767        overseerr:5055     tdarr:8265-6
autobrr:7474       cross-seed:2468    decluttarr
flaresolverr:8191

REMOVED: gluetun, qbittorrent (now on laptop)
```

### Laptop (2 containers)
```
gluetun: qmcgaw/gluetun (AirVPN, killswitch)
qbittorrent: lscr.io/linuxserver/qbittorrent:4.6.3 (network_mode: gluetun)
  CPU: 2 cores, RAM: 3.5GB, vol: /mnt/server/downloads:/downloads
```

---

## 5. SERVICE PORTS

```
qBit:       http://<laptop-ip>:8080    (topaz / see info file)
Radarr:     http://<server-ip>:7878    API: see info
Sonarr:     http://<server-ip>:8989    API: see info
Prowlarr:   http://<server-ip>:9696    API: see info
Plex:       http://<server-ip>:32400   (Plex email — see info file)
Dashboard:  http://<server-ip>:8090
Overseerr:  http://<server-ip>:5055
Tdarr:      http://<server-ip>:8265
```

---

## 6. DOWNLOAD FLOW (END-TO-END)

```
1. REQUEST:  Overseerr → Radarr/Sonarr OR RSS catch OR discovery
2. SEARCH:   Radarr/Sonarr → Prowlarr → 10 indexers
3. DOWNLOAD: qBit(laptop) → gluetun → WireGuard → AirVPN
             Write: /downloads/ (container) = NFS = server /mnt/20TB/homelab/media/downloads/
4. IMPORT:   Radarr/Sonarr poll qBit → detect 100% → import to media folder
             Remote map: /downloads/ → /mnt/20TB/homelab/media/downloads/
             removeCompleted=TRUE → qBit torrent removed (deleteFiles=false)
5. PROCESS:  Plex auto-scans → poster/art → tdarr(midnight-10am) HEVC encode
             Bazarr subtitles | decluttarr cleanup | cross-seed matching
6. STREAM:   Remote → port 32400 → Plex → GPU NVENC transcode (temp: /tmp RAM)
```

---

## 7. ALL TIMERS

### Server (22 timers)
```
torrent-doctor       every 10m    Inject 37 trackers, recheck stalled
tdarr-post-encode    every 5m     Replace encoded originals
cleanup-completed    every 5m     Laptop: remove completed qBit torrents
vpn-watchdog         every 60s    Laptop: restart gluetun if dead
disk-space-guard     every 15m    Disk space alerts
health-score         every 30m    Generate HEALTH_SCORE.json
balance-8tb          every 30m    Move 8TB→20TB at 85%
seed-finder          every 30m    Re-announce stalled
smart-fill           every 30m    Add missing episodes when qBit <150
disk-watchdog        every 30m    SMART disk health
crash-watchdog       every 5m     Crash detection
healer-check         every 5m     Laptop: health check server
completed-import     every 2m     Backup import safety net
protect-8tb          hourly       Disable 8TB roots at ≥98%
complete-media       every 6h     Find missing seasons/episodes/sequels
auto-dedup           every 6h     Safe full-scan dedup
taste-daily          daily 2:30am Update watch counts + genre scores
discovery-engine     daily 2am    TMDB scan + scoring + plexlist
nightly-backup       daily 3am    Export all configs → desktop
pipeline-gc          daily 4am    Cleanup candidates/logs
taste-weekly         Sun 3am      Director/actor affinity from TMDB
discovery-weekly     Sun 3am      Deep scan + taste update
taste-monthly        1st 5am      Rebuild + score decay
discovery-monthly    1st 4am      Full sweep
taste-yearly         Jan 1 6am    Complete reset + re-learn
discovery-yearly     Jan 1 5am    Complete refresh
```

---

## 8. QBITTORRENT TUNING

```
Active DL:15   Max Torrents:200   Active UL:15
Cache:1536MB   Disk Queue:32MB    Connections:5000/500
Port:51413     Encryption:required   Prealloc:ON
DHT/PEX/LSD:ON  Queueing:ON  AnnAll:ON
Save: /downloads/ → NFS → server 20TB
Categories: radarr, sonarr
Creds: topaz / see info file
37 public trackers injected every 10min
```

---

## 9. QUALITY PROFILES

### Radarr HD-720p/1080p (ID=6)
```
Upgrades: YES, Cutoff: Bluray-1080p
Allowed: HDTV-720p, WEB-720p, Bluray-720p, HDTV-1080p, WEB-1080p, Bluray-1080p
Language: English default, dual audio for foreign/anime
Download client: <laptop-ip>:8080, removeCompleted=TRUE
Remote map: /downloads/ → /mnt/20TB/homelab/media/downloads/
Root folders: /mnt/20TB/Movies 1 (7.5TB), /mnt/8TB/Movies 2 (1.2TB)
```

### Sonarr HD-720p (ID=3)
```
Upgrades: YES, Cutoff: Bluray-720p
Allowed: HDTV-720p, WEB-720p, Bluray-720p
Language: English default, dual audio for foreign/anime
Download client: <laptop-ip>:8080, removeCompleted=TRUE
Remote map: /downloads/ → /mnt/20TB/homelab/media/downloads/
Root folders: /mnt/20TB/TV Shows 1 (7.5TB), /mnt/8TB/TV Shows 2 (1.2TB)
```

---

## 10. PIPELINE DIRECTORY

```
/mnt/20TB/homelab/media/Pipeline/
├── discovery/           v4.0 engine (priority hierarchy, 4 queues)
│   ├── engine.py        orchestrator
│   ├── taste.py         multi-user taste (daily/weekly/monthly/yearly)
│   └── scoring.py       confidence scoring + 4 queues
├── safeguards/
│   ├── guard.py         storage/health circuit breakers
│   └── rules.json       complete_only_mode, thresholds, limits
├── taste/               per-user profiles (auto-detected)
├── candidates/          auto_add, review, quarantine, rejected
├── scripts/             17 automation scripts
├── knowledge/           liked, disliked, never_again, favorites
├── logs/                unified logging
├── state/               HEALTH_SCORE.json, snapshots
├── plexlist.txt         3,234 lines master content seed
├── MASTER_BLUEPRINT.md  architecture blueprint
└── KNOWN_BAD.md         institutional memory
```

---

## 11. DISCOVERY ENGINE

```
Priority: P1 manual → P2 missing → P3 seeds → P4 gaps → P5 related → P6 trending → P7 taste

Seed types in plexlist.txt:
  # Title    = owned (auto-commented)
  @Actor     = scan filmography (+50 pts)
  @Director  = scan filmography (+70 pts)
  +TMDB_ID   = fill franchise (+80 pts)
  %Genre     = genre discovery (+35 pts)
  ~Movie     = similar content (+45 pts)

Confidence queues:
  ≥80% → auto_add → Radarr (monitored+searched)
  50-80% → review_queue
  30-50% → quarantine
  <30% → rejected

Mode: complete_only (only fills gaps in existing content)
```

---

## 12. TASTE ENGINE

```
v4.0: Multi-user, multi-source, multi-schedule
Sources: Plex watch data + TMDB credits + Radarr fallback
Dimensions: genres, directors, actors, decades
Scoring: 0.15-3.00 (1.00 = neutral default)
Auto-detects: ALL named Plex users (currently topazconch + astrotopaz)

Schedule: Daily(2:30am) watch counts, Weekly(Sun 3am) director/actor,
          Monthly(1st 5am) rebuild+decay, Yearly(Jan 1 6am) reset

Per-user profiles: taste/{username}.json (created on first detection)
Global profile: taste/global_profile.json (weighted merge)
```

---

## 13. RECOVERY

### Rebuild Confidence
```
qBit recovery:     VERIFIED (100%, 5 min)
Plex restore:      VERIFIED (95%, 15 min)
*arr DB restore:   VERIFIED (90%, 10 min)
Server rebuild:    PARTIAL (70%)
Total loss:        THEORETICAL (10%)
```

### Quick Recovery
```
LAPTOP DIES: Any Linux box. IP <laptop-ip>. Restore /home/laptop/pipeline/ from backup. docker-compose up.
SERVER DIES: Install Arch. Restore compose+fstab. docker compose up. systemctl enable plexmediaserver.
PLEX DB CORRUPT: Stop Plex. Restore /var/lib/plex from backup. Start Plex.
20TB DEAD: Replace drive. Format. Restore configs. *arr re-downloads all media.
```

---

## 14. KNOWN BAD — NEVER DO

```
NEVER mount Samsung 970 EVO Plus (nvme0n1) — controller lockup, D-state hangs
NEVER enable laptop WiFi (wlp5s0) — MASKED, ethernet only
NEVER run qBittorrent on server — 479 torrents = 75% I/O wait
NEVER run gluetun on server — VPN on laptop only
NEVER put Plex metadata on NTFS — Sqlite3 timeouts
NEVER allow qBit local disk downloads — NFS only
NEVER edit Plex Preferences.xml while Plex running
```

---

## 15. COUNTS (2026-07-03)

```
Plex:     593 movies, 465 shows
Radarr:   2,174 movies (207 downloaded, 1,967 missing)
Sonarr:   200 shows (3,264/15,242 episodes, 11,978 missing)
qBit:     1,948 torrents (6 active, 1,931 queued, DL:1.3MB/s, DHT:360)
20TB:     64% (7.5TB free) | 8TB: 85% (1.2TB free)
Health:   59/100 (8TB storage penalty)
Timers:   22 active
```

---

## 16. CREDENTIALS (references — raw values in /home/topaz/home/info)

```
qBit:        http://<laptop-ip>:8080  (topaz / see info)
Radarr API:  see info (e7746c...)
Sonarr API:  see info (1b24c...)
Prowlarr API: see info (1a32c...)
TMDB API:    see info (5e00e...)
Plex token:  see info (BJm8t...)
Server SSH:  <user>@<server-ip> -p 2223
Laptop SSH:  laptop@<laptop-ip> -p 2225
VPN:         AirVPN WireGuard (keys in info file)
```

---


## 18. SECURITY POSTURE

### Secrets Management
- ALL raw credentials stored in: `/home/topaz/home/info` (NOT in .md files)
- All .md files reference "see info file" — never contain actual keys/passwords
- Recommended: encrypt info file with GPG or use a password manager

### Credential Rotation Checklist
After any credentials appear in logs, chat, or documentation:
- [ ] Rotate qBit password
- [ ] Rotate Radarr API key (Settings → General)
- [ ] Rotate Sonarr API key (Settings → General)
- [ ] Rotate Prowlarr API key (Settings → General)
- [ ] Rotate Plex token (plex.tv/claim)
- [ ] Download new AirVPN WireGuard config
- [ ] Update all pipeline scripts with new credentials
- [ ] Update systemd Environment variables
- [ ] Verify pipeline still works

### Current Status
- qBit password: ROTATED (2026-06-30)
- *arr API keys: rotation pending
- Plex token: rotation pending
- AirVPN keys: rotation pending
- Documentation: CLEAN (no raw secrets in .md files)


## 17. COMMANDS REFERENCE

```
# Health check
ssh server pipeline-check

# Web UIs
http://<server-ip>:7878 (Radarr)    http://<server-ip>:8090 (Dashboard)
http://<server-ip>:8989 (Sonarr)    http://<server-ip>:32400 (Plex)
http://<laptop-ip>:8080 (qBit)      http://<server-ip>:9696 (Prowlarr)

# Manual actions
ssh server /mnt/20TB/homelab/media/Pipeline/scripts/scan-now.sh  (discovery)
ssh server python3 /mnt/20TB/homelab/media/Pipeline/scripts/complete-media.py
ssh server python3 /mnt/20TB/homelab/media/Pipeline/scripts/auto-dedup.py
ssh server /mnt/20TB/homelab/media/Pipeline/scripts/balance-8tb.sh

# Logs
ssh server tail -50 /mnt/20TB/homelab/media/Pipeline/logs/discovery-engine.log
ssh server tail -20 /mnt/20TB/homelab/media/Pipeline/logs/torrent-doctor.log

# Drive check
ssh server df -h /mnt/20TB /mnt/8TB /

# qBit check
ssh server 'curl -sL http://<laptop-ip>:8080/api/v2/auth/login --data-urlencode username=topaz --data-urlencode password=(see info file)'
```
