# RECOVERY — Complete Rebuild From Scratch (1:1)
# Updated: 2026-07-14 — Pipeline v7.1
# Covers EVERYTHING to rebuild the entire homelab from bare metal.

---

## OVERVIEW
3 machines + 16 Docker containers + systemd timers + gaming VM.
Rebuild order: Server first, then Laptop, then Desktop.

---

## PHASE 1: SERVER REBUILD (10.0.0.200)

### 1.1: Install Ubuntu 24.04 LTS
- Boot from USB, install Ubuntu Server 24.04 LTS
- Username: topaz, password: USER_PASSWORD
- Enable OpenSSH server during install
- Disk layout:
  - /dev/sda (120GB SSD): OS root (ext4)
  - /dev/sdb (20TB Seagate Exos): /mnt/20TB (ext4)
  - /dev/sdc (8TB Seagate): /mnt/8TB (ext4)
  - /dev/nvme0n1 (1.8TB Samsung 970 EVO Plus): /mnt/nvme (ext4)

### 1.2: Mount Drives
```bash
sudo blkid /dev/sdb2 /dev/sdc2 /dev/nvme0n1p1
# Add to /etc/fstab (use actual UUIDs):
UUID=<20TB-UUID>  /mnt/20TB  ext4  defaults,noatime,nofail  0  2
UUID=<8TB-UUID>   /mnt/8TB   ext4  defaults,noatime,nofail  0  2
UUID=<NVMe-UUID>  /mnt/nvme  ext4  defaults,noatime,nofail  0  2
sudo mount -a
```

### 1.3: Create Media Directories
```bash
sudo mkdir -p "/mnt/20TB/Movies 1" "/mnt/20TB/TV Shows 1"
sudo mkdir -p "/mnt/8TB/Movies 2" "/mnt/8TB/TV Shows 2"
sudo mkdir -p /mnt/20TB/homelab/media/downloads
sudo mkdir -p /mnt/20TB/homelab/media/compose
sudo mkdir -p /mnt/nvme/pipeline-logs /mnt/nvme/vm
sudo chown -R topaz:topaz /mnt/20TB /mnt/8TB /mnt/nvme
```

### 1.4: Install Docker
```bash
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker topaz
sudo mkdir -p /etc/docker
cat << 'DEOF' | sudo tee /etc/docker/daemon.json
{
  "data-root": "/mnt/8TB/docker-data",
  "dns": ["1.1.1.1", "8.8.8.8"],
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
DEOF
sudo systemctl enable docker
sudo systemctl start docker
```

### 1.5: Install System Packages
```bash
sudo apt update
sudo apt install -y curl wget git python3 python3-pip net-tools nftables ufw \
  smartmontools lm-sensors samba nfs-kernel-server \
  virt-manager libvirt-daemon-system qemu-kvm \
  unattended-upgrades ethtool
```

### 1.6: Configure SSH Key Auth
```bash
# On CachyOS desktop:
ssh-keygen -t ed25519 -f ~/.ssh/server_ed25519 -N ""
ssh-copy-id -i ~/.ssh/server_ed25519 -p 2223 topaz@10.0.0.200

# On server:
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### 1.7: Configure Firewall
```bash
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 2223/tcp comment 'SSH-LAN'
sudo ufw enable

# fix-nftables.service (see full unit in SERVICES.md)
sudo systemctl enable fix-nftables
sudo systemctl start fix-nftables
```

### 1.8: Create Pipeline Config
```bash
sudo mkdir -p /etc/pipeline
# Copy config.json from this documentation (see README.md CREDENTIALS section)
sudo chmod 600 /etc/pipeline/config.json
```

### 1.9: Deploy Docker Compose
```bash
cd /mnt/20TB/homelab/media/compose
# Copy docker-compose.yml, config.env, .env from this documentation
# Create service config directories for each container
# .env must have perms 600
chmod 600 .env
docker compose up -d
```

### 1.10: Install Pipeline Scripts
```bash
# Copy all scripts to /opt/ (see README.md PIPELINE SCRIPTS section)
sudo chmod +x /opt/*.py /opt/*.sh
sudo chown root:root /opt/*.py /opt/*.sh
```

### 1.11: Create Systemd Timers
```bash
# Create service + timer pairs (see TIMERS.md for full schedule)
sudo systemctl daemon-reload
sudo systemctl enable --now anti-seed.timer autonomous-pipeline.timer \
  batch-import.timer health-monitor.timer recovery-sync.timer media-dedupe.timer
```

### 1.12: Install Plex
```bash
curl https://downloads.plex.tv/plex-keys/PlexSign.key | gpg --dearmor | \
  sudo tee /usr/share/keyrings/plex-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/plex-archive-keyring.gpg] \
  https://downloads.plex.tv/repo/deb public main" | \
  sudo tee /etc/apt/sources.list.d/plexmediaserver.list
sudo apt update && sudo apt install -y plexmediaserver
sudo systemctl enable plexmediaserver
# Add libraries via web UI at http://10.0.0.200:32400
```

### 1.13: Install Samba
```bash
# Copy smb.conf from SERVICES.md
sudo systemctl enable smbd nmbd
sudo systemctl start smbd nmbd
sudo smbpasswd -a topaz  # Password: USER_PASSWORD
```

### 1.14: Gaming VM
```bash
sudo apt install -y virt-manager libvirt-daemon-system qemu-kvm
sudo systemctl enable libvirtd
sudo systemctl start libvirtd
# Copy gaming-vm.service from SERVICES.md
sudo virsh autostart win10-gaming
```

### 1.15: NIC Tuning
```bash
sudo ethtool --set-wol enp10s0 g
sudo sysctl -w net.ipv4.tcp_keepalive_time=60
sudo sysctl -w net.ipv4.tcp_keepalive_intvl=10
sudo sysctl -w net.ipv4.tcp_keepalive_probes=6
sudo sysctl -w vm.swappiness=10
# Persist in /etc/sysctl.d/99-homelab.conf
```

### 1.16: Auto-Updates
```bash
cat << 'UEOF' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
UEOF
```

### 1.17: Mask Failed Services
```bash
sudo systemctl mask nftables.service
sudo systemctl mask transmission-daemon.service
sudo systemctl mask fwupd.service
sudo systemctl mask fwupd-refresh.service
```

---

## PHASE 2: LAPTOP REBUILD (10.0.0.192)

### 2.1: Install Ubuntu Server
- Username: topaz, password: USER_PASSWORD
- Static IP: 10.0.0.192/24, gateway 10.0.0.1, DNS 1.1.1.1
- SSH port: 2224

### 2.2: Install Packages
```bash
sudo apt update
sudo apt install -y python3 python3-pip curl wget net-tools
```

### 2.3: Deploy Services
```bash
# Install Uptime Kuma
# Install Heimdall
# Copy health-monitor.py to /opt/
# Create health-monitor cron job (every 5 min)
```

### 2.4: Configure SSH
```bash
# Set port 2224 in /etc/ssh/sshd_config
# Deploy SSH key from desktop
# Disable password auth
sudo systemctl restart sshd
```

---

## PHASE 3: DESKTOP REBUILD (10.0.0.234)

### 3.1: Install CachyOS
- Username: topaz, password: USER_PASSWORD
- KDE Plasma 6.7 Wayland
- RTX 3080, driver 610.43.03

### 3.2: Configure Network
```bash
# Static IP or DHCP reservation for 10.0.0.234
# VPN: AirVPN WireGuard (separate config from server)
```

### 3.3: Samba Mounts
```bash
# /etc/fstab entries:
//10.0.0.200/server-20TB  /mnt/server-20TB  cifs  credentials=/etc/samba/creds-server,uid=1000,gid=1000  0  0
//10.0.0.200/server-8TB   /mnt/server-8TB   cifs  credentials=/etc/samba/creds-server,uid=1000,gid=1000  0  0
```

### 3.4: Moonlight Client
- Install Moonlight
- Connect to gaming VM at 10.0.0.200

---

## PHASE 4: RESTORE DATA

### 4.1: If Drives Are Intact
- Mount drives, Plex will auto-detect libraries
- Radarr/Sonarr will scan existing media
- qBit will resume downloads

### 4.2: If Drives Are Lost
- have-list.txt is the master recovery list
- /opt/recovery.py scans disk vs Radarr/Sonarr
- Radarr/Sonarr will re-download missing content

### 4.3: Full Rebuild From have-list.txt
```bash
python3 /opt/recovery.py
# This scans all media dirs, compares against Radarr/Sonarr
# Reports what's missing and what can be re-downloaded
```

---

## PHASE 5: VERIFY EVERYTHING

```bash
# Check all containers
docker ps --format '{{.Names}}\t{{.Status}}'

# Check all timers
systemctl list-timers --all

# Check pipeline
python3 /opt/autonomous-pipeline.py  # Should complete without errors

# Check batch import
python3 /opt/batch_import.py  # Should complete without errors

# Check firewall
nft list chain ip filter INPUT  # Should have 26+ rules

# Check qBit
curl -s -4 http://127.0.0.1:8083/api/v2/torrents/info | python3 -c "import json,sys; print(f'{len(json.load(sys.stdin))} torrents')"

# Check Sonarr/Radarr
curl -s http://localhost:8989/api/v3/series -H 'X-Api-Key: SONARR_API_KEY' | python3 -c "import json,sys; print(f'{len(json.load(sys.stdin))} series')"
curl -s http://localhost:7878/api/v3/movie -H 'X-Api-Key: RADARR_API_KEY' | python3 -c "import json,sys; print(f'{len(json.load(sys.stdin))} movies')"

# Check Plex
curl -s http://localhost:32400 -H 'X-Plex-Token: PLEX_TOKEN' | head -1
```

---

## BACKUP SCHEDULE

| What                  | Where                    | When    |
|-----------------------|--------------------------|---------|
| Pipeline configs      | /mnt/20TB/homelab/       | Live    |
| Docker compose        | /mnt/20TB/homelab/media/compose/ | Live |
| Pipeline scripts      | /opt/                    | Live    |
| systemd units         | /etc/systemd/system/     | Live    |
| Pipeline-Doc          | /mnt/20TB/homelab/media/Pipeline/Pipeline-Doc/ | Manual |
| CachyOS docs          | /home/topaz/Documents/Documention/ | Manual |

---

## EMERGENCY COMMANDS

```bash
# Kill stuck containers
sudo systemctl stop docker.socket docker
sudo pkill -9 dockerd containerd
sudo rm -rf /var/run/docker/runtime-runc/moby/*
sudo systemctl start docker
cd /mnt/20TB/homelab/media/compose && docker compose up -d

# 20TB drive recovery
sudo umount -l /mnt/20TB
sudo fsck -fy /dev/sdb2
sudo mount /dev/sdb2 /mnt/20TB

# Force re-add missing content
curl -X POST http://localhost:8989/api/v3/command -H "X-Api-Key: SONARR_API_KEY" -d '{"name":"MissingEpisodeSearch"}'
curl -X POST http://localhost:7878/api/v3/command -H "X-Api-Key: RADARR_API_KEY" -d '{"name":"MissingMoviesSearch"}'

# Restart pipeline
sudo systemctl restart autonomous-pipeline.timer

# Check VPN
docker logs gluetun-overflow --tail 10
```
