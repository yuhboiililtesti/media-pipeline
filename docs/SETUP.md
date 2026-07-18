# Pipeline Setup Guide

This is the exact setup I use. Adapt paths, IPs, and ports to your environment.

## Hardware You Need

- **Storage**: At least one large drive. I have a 20TB (primary) and 8TB (overflow).
- **Laptop (optional)**: A second machine for VPN-isolated qBittorrent. I use an old Ubuntu laptop.

## Step 1: Clone

```bash
git clone https://github.com/yuhboiililtesti/media-pipeline
cd media-pipeline
```

## Step 2: Set Up Docker

Create a Docker network:

```bash
docker network create media-net
```

Deploy the stack (example `docker-compose.yml` included in `systemd/`):

```bash
docker compose up -d
```

Services: Radarr, Sonarr, Prowlarr, Plex, Tdarr, Overseerr, Bazarr, FlareSolverr, cross-seed, decluttarr, autobrr, gluetun-overflow, qbittorrent-overflow.

## Step 3: Configure VPN qBittorrent

I run two qBit instances:

1. **Overflow** (server, port 8083): Behind gluetun WireGuard VPN. Handles TV backlog.
2. **Laptop** (separate machine, port 8080): Behind its own gluetun WireGuard VPN. Handles movies + backup TV.

The `pipeline` command controls both simultaneously.

## Step 4: Mount Drives

Server `/etc/fstab`:
```
/dev/sda2  /mnt/20TB  ntfs-3g  rw,uid=1000,gid=1000,noatime  0 0
/dev/sdc2  /mnt/8TB   ntfs-3g  rw,uid=1000,gid=1000,noatime  0 0
```

Laptop NFS mount for downloads:
```
server-ip:/mnt/20TB/homelab/media/downloads  /mnt/server/downloads  nfs4  rw,vers=4.2,soft,noatime  0 0
```

**Important**: Format drives as ext4 if possible. NTFS on Linux is slow under concurrent I/O.

## Step 5: Set API Keys

Copy `.env.example` to `.env` and fill in your actual keys:

```bash
cp .env.example .env
# Edit .env with your real keys
```

Get a free TMDB key: https://www.themoviedb.org/settings/api

## Step 6: Install Pipeline Commands

```bash
sudo cp systemd/pipeline-commands.sh /usr/local/bin/
# Or just run the commands from the repo directory
```

## Step 7: Install Systemd Timers

```bash
sudo cp systemd/*.timer systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pipeline-max.timer pipeline-day.timer
sudo systemctl enable torrent-doctor.timer auto-import.timer
sudo systemctl enable anti-dupe.timer protect-20tb.timer
sudo systemctl enable nightly-backup.timer discovery-engine.timer
# ... enable the rest as needed
```

## Step 8: Seed Your Taste Profile

Edit `plexlist.txt` with content you like:

```
[ACTORS]
@Tom Hanks
@Cate Blanchett

[DIRECTORS]
@Christopher Nolan
@Denis Villeneuve

[FRANCHISES]
+10       # Star Wars
+13151    # Marvel Cinematic Universe

[GENRES]
%Science Fiction
%Horror

[SIMILAR]
~Inception
~The Matrix
```

The discovery engine scans TMDB for everything these people have made, everything in these franchises, popular movies in these genres, and movies similar to your seeds.

## Step 9: Verify

```bash
pipeline-health    # quick check everything is alive
pipeline-max       # start downloading
pipeline-stall     # check if flow is working
pipeline-help      # see all commands
```

## My Actual Layout

```
/mnt/20TB/
├── Movies 1/           # primary movie library (Plex)
├── TV Shows 1/         # primary TV library (Plex)
├── Encode-Tmp/         # Tdarr transcode cache
└── homelab/
    └── media/
        ├── Pipeline/   # all pipeline scripts + state
        │   ├── scripts/
        │   ├── discovery/
        │   ├── safeguards/
        │   ├── taste/
        │   ├── candidates/
        │   ├── logs/
        │   ├── have-list.txt
        │   └── plexlist.txt
        ├── compose/    # docker-compose.yml + container configs
        └── downloads/  # qBit download directory (NFS shared)

/mnt/8TB/
├── Movies 2/           # overflow movie library
└── TV Shows 2/         # overflow TV library

/var/lib/plex/          # Plex metadata (MUST be on SSD, NOT NTFS)
/tmp/                   # Plex transcode (RAM)
```

## Troubleshooting

**Downloads stopped?**
```bash
pipeline-stall     # tells you exactly why
pipeline-unstall   # emergency restart everything
```

**Disk full?**
The pipeline protects itself — slows at 90%, stops at 98%. Check with:
```bash
pipeline-space
pipeline-clean     # free up space
```

**Same episode downloading twice?**
Anti-dupe runs every 30min. Force it:
```bash
pipeline-clean
```

**Server rebooted?**
```bash
pipeline-recover   # NFS remount + compose validate + restart + MAX mode
```
