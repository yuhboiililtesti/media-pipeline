# Commands Reference

> All useful commands organized by category. Copy-paste ready. CachyOS desktop unless noted otherwise.

---

## VM Commands (CachyOS)

| Command | Description |
|---------|-------------|
| `vm moon` | Moonlight stream — connects to VM via GPU NVENC hardware encoding |
| `vm spice` | SPICE viewer — QXL removed, may not work (use `vm moon`) |
| `vm ssh` / `ssh vm` | SSH into Windows VM (port 2225) |
| `vm status` | Show VM running state (`shut off` / `running`) |

---

## Pipeline Commands (CachyOS)

| Command | Description |
|---------|-------------|
| `pipeline status` | Live: pipeline logs, timers, docker, media counts, VM state |
| `pipeline dedup` | Show last deduplication results + space recovered |
| `pipeline health` | Disk usage (20TB/8TB/NVMe) + container health |
| `pipeline log [N]` | Tail last N lines of pipeline log (default 20) |
| `pipeline search` | Trigger missing movies + TV backlog search |
| `pipeline restart` | Restart autonomous-pipeline timer |
| `pipeline help` | Show all available commands |

---

## SSH (CachyOS)

| Command | Description |
|---------|-------------|
| `ssh server` | SSH into Ubuntu server (10.0.0.200:2223, key auth) |
| `ssh vm` | SSH into Windows VM (10.0.0.200:2225, password USER_PASSWORD) |
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

## Server — libvirt / QEMU

| Command | Description |
|---------|-------------|
| `sudo virsh list --all` | List all VMs with state |
| `sudo virsh start win10-gaming` | Boot the VM |
| `sudo virsh shutdown win10-gaming` | Graceful ACPI shutdown (preferred) |
| `sudo virsh destroy win10-gaming` | Force power-off — NEVER use if GPU passthrough is active (GPU reset bug) |
| `sudo virsh dominfo win10-gaming` | Detailed VM info — CPU, memory, UUID, autostart |
| `sudo virsh domifaddr win10-gaming` | Show VM IP address |
| `sudo virsh net-dhcp-leases default` | Show DHCP leases on NAT network |
| `sudo virsh net-start default` | Start libvirt NAT network |
| `sudo virsh dumpxml win10-gaming` | Export VM XML (backup/debug) |
| `sudo virsh define /path/to/vm.xml` | Import VM from XML |
| `sudo virsh autostart win10-gaming` | Enable autostart on host boot |
| `sudo virsh domdisplay win10-gaming` | Show SPICE display address |

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
| `sudo iptables -t nat -L PREROUTING -n` | NAT port forward rules (Sunshine: 47989, SSH: 2225) |
| `sudo nft list ruleset` | Full nftables firewall rules |
| `curl -s http://127.0.0.1:8083/` | qBit WebUI health check |
| `curl -s http://localhost:47989/serverinfo` | Sunshine health check (from server) |

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
| Sunshine (VM) | http://10.0.0.200:47990 |

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
| COLD BOOT | Physical power cycle — ONLY fix for GPU zombie state |
| `sudo /opt/gpu-reset.sh` | Attempt GPU recovery (rarely works) |
| `sudo virsh define /mnt/20TB/homelab/backup/vm/passthrough-win10-golden.xml` | Restore golden VM XML |
| `sudo python3 /opt/dedupe_media.py` | Run deduper manually |
| `sudo systemctl restart autonomous-pipeline.timer` | Restart pipeline timer |

---

## Windows VM (via SSH: `ssh vm`)

| Command | Description |
|---------|-------------|
| `nvidia-smi` | GPU status — temp, driver, processes |
| `sc query Sunshine` | Check Sunshine service |
| `powershell Start-Process 'C:\Program Files\Sunshine\sunshine.exe' -WindowStyle Hidden` | Start Sunshine manually |
| `sc query sshd` | Check OpenSSH service |
| `powercfg /getactivescheme` | Check power plan (should be High Performance) |
| `netstat -an \| findstr 47989` | Check Sunshine port |
| `netsh advfirewall firewall add rule name="Sunshine TCP" dir=in action=allow protocol=TCP localport=47984,47989,47998,48010` | Add firewall rule |
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

## NVIDIA Driver

| Item | Value |
|------|-------|
| GPU | GTX 1660 SUPER (TU116) |
| VM Driver | 560.94 (stable, proven with VFIO) |
| NVENC | Turing 6th-gen, HEVC B-frames NOT supported |
| Passthrough | All 4 PCI functions (0b:00.0–0b:00.3), managed=no |

---

## GPU Reset Bug — Rules

| Rule | Detail |
|------|--------|
| NEVER `virsh destroy` | Forces GPU zombie state — cold boot required |
| NEVER Windows Restart | Produces phantom GPU — shut down Windows instead |
| ALWAYS Shut Down | Clean GPU driver unload, no phantom state |
| COLD BOOT = Clean GPU | Only guaranteed recovery after zombie state |

---

*Last updated: 2026-07-15 — Pipeline v7.2*
