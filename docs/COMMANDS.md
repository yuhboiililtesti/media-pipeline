# Commands Reference


---


| Command | Description |
|---------|-------------|

---


| Command | Description |
|---------|-------------|
| `pipeline dedup` | Show last deduplication results + space recovered |
| `pipeline log [N]` | Tail last N lines of pipeline log (default 20) |
| `pipeline search` | Trigger missing movies + TV backlog search |
| `pipeline restart` | Restart autonomous-pipeline timer |
| `pipeline help` | Show all available commands |

---


| Command | Description |
|---------|-------------|
| `ssh server` | SSH into Ubuntu server (10.0.0.200:2223, key auth) |
| `ssh laptop` | SSH into laptop (10.0.0.234:2225, user=laptop) |

---

## Server — Pipeline Scripts (/opt/)

| Script | Timer | Purpose |
|--------|-------|---------|
| `autonomous-pipeline.py` | every 10min | 14-module master controller |
| `batch_import.py` | every 30min | Sort downloads to media dirs |
| `anti-seed.py` | every 2min | Delete dead/zero-seed torrents |
| `health-monitor.py` | every 5min | Auto-restart failed containers |
| `recovery.py` | daily | Disk vs Radarr/Sonarr scan |
| `dedupe_media.py` | daily | Hash-verified cross-drive dedup |

---


| Command | Description |
|---------|-------------|
| `sudo virsh net-dhcp-leases default` | Show DHCP leases on NAT network |

---

## Server — Docker

| Command | Description |
|---------|-------------|
| `docker ps` | List running containers |
| `docker ps --format 'table {{.Names}}\t{{.Status}}'` | Clean format |
| `docker logs <container> --tail 50` | Last 50 log lines |
| `docker restart <container>` | Restart container |
| `docker compose up -d` | Start pipeline stack (from compose dir) |
| `docker compose down` | Stop stack |
| `docker stats --no-stream` | Resource usage snapshot |

---

## Server — Networking

| Command | Description |
|---------|-------------|
| `ss -tlnp` | All listening TCP ports |
| `sudo nft list ruleset` | Full nftables firewall rules |
| `curl -s http://127.0.0.1:8083/` | qBit WebUI health check |

---

## Server — Service URLs

| Service | URL |
|---------|-----|
| Plex | http://10.0.0.200:32400 |
| qBit | http://10.0.0.200:8083 |
| Sonarr | http://10.0.0.200:8989 |
| Radarr | http://10.0.0.200:7878 |
| Prowlarr | http://10.0.0.200:9696 |
| Bazarr | http://10.0.0.200:6767 |
| Overseerr | http://10.0.0.200:5055 |
| Tdarr | http://10.0.0.200:8265 |
| Cross-seed | http://10.0.0.200:2468 |
| Autobrr | http://10.0.0.200:7474 |
| Immich | http://10.0.0.200:2283 |

---

## Server — API Keys

| Service | API Key |
|---------|---------|
| Radarr | `RADARR_API_KEY` |
| Sonarr | `SONARR_API_KEY` |
| Prowlarr | `PROWLARR_API_KEY` |
| Plex Token | `PLEX_TOKEN` |

---

## Server — *Arr API Triggers

| Command | Description |
|---------|-------------|
| `curl -X POST localhost:7878/api/v3/command -H 'X-Api-Key: <KEY>' -d '{"name":"RefreshMovies"}'` | Radarr library refresh |
| `curl -X POST localhost:8989/api/v3/command -H 'X-Api-Key: <KEY>' -d '{"name":"RescanSeries"}'` | Sonarr library rescan |
| `curl -X POST localhost:7878/api/v3/command -H 'X-Api-Key: <KEY>' -d '{"name":"MissingMoviesSearch"}'` | Radarr search missing |
| `curl -X POST localhost:8989/api/v3/command -H 'X-Api-Key: <KEY>' -d '{"name":"MissingEpisodeSearch"}'` | Sonarr search missing |
| `curl -X POST localhost:7878/api/v3/command -H 'X-Api-Key: <KEY>' -d '{"name":"RenameAllFiles"}'` | Radarr rename all files |

---

## Server — Emergency / Recovery

| Command | Description |
|---------|-------------|
| `sudo reboot` | Warm reboot |
| `sudo python3 /opt/dedupe_media.py` | Run deduper manually |
| `sudo systemctl restart autonomous-pipeline.timer` | Restart pipeline timer |

---


| Command | Description |
|---------|-------------|
| `sc query sshd` | Check OpenSSH service |
| `powercfg /getactivescheme` | Check power plan (should be High Performance) |
| `shutdown /r /t 0` | Reboot Windows |
| `shutdown /s /t 0` | Shutdown Windows |

---

## Media Directories

| Path | Contents |
|------|----------|
| `/mnt/20TB/Movies 1` | Primary movies |
| `/mnt/20TB/TV Shows 1` | Primary TV shows |
| `/mnt/8TB/Movies 2` | Secondary movies |
| `/mnt/8TB/TV Shows 2` | Secondary TV shows |
| `/mnt/20TB/homelab/media/downloads` | Active torrent downloads |

---


| Item | Value |
|------|-------|
| NVENC | Turing 6th-gen, HEVC B-frames NOT supported |
| Passthrough | All 4 PCI functions (0b:00.0–0b:00.3), managed=no |

---


| Rule | Detail |
|------|--------|

---

*Last updated: 2026-07-15 — Pipeline v7.2*
