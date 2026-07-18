# Automation Documentation

## Overview

All automated services, scripts, cron jobs, systemd units, scheduled tasks, and watchdog processes across the Topaz server infrastructure.

---

## Systemd Services

### Enabled Services Summary

| Service                     | Purpose                                 | Auto-start |
|-----------------------------|-----------------------------------------|------------|
| `plexbot.service`           | Discord bot for Plex status             | Yes        |
| `gluetun-qbit-sync.service` | Sync qBit port after VPN reconnect      | Yes        |
| `qbit-watchdog.service`     | Restart qBittorrent if unresponsive     | Yes        |
| `fail2ban.service`          | SSH brute-force protection              | Yes        |
| `netfilter-persistent`      | Restore iptables rules on boot          | Yes        |

---


### Unit File

```ini
[Unit]

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/bin/sleep 10
ExecStartPre=/opt/phantom-check.sh
TimeoutStartSec=300
User=root

[Install]
WantedBy=multi-user.target
```

### Boot Sequence

```
0s   → systemd starts the unit
```

### phantom-check.sh

```bash
#!/bin/bash


if [ "$DRIVER" != "vfio-pci" ]; then
    exit 1
fi
```

---

## Anti-Seed

### Overview

Prevents excessive seeding by monitoring torrent ratios and removing completed torrents that exceed target ratio thresholds.

### Script

```
Location: /opt/anti-seed.py
```

### Cron

```cron
*/2 * * * * /usr/bin/python3 /opt/anti-seed.py >> /var/log/anti-seed.log 2>&1
```

### Step-by-Step Logic

1. **Connect to qBittorrent API** at `localhost:8083` with credentials `topaz:USER_PASSWORD`
2. **Fetch all torrents** via `/api/v2/torrents/info`
3. **Iterate each torrent** and check:
   - State is `uploading` or `stalledUP` or `checkingUP` (seeding states)
   - Ratio ≥ target ratio (default: 3.0 for public, 5.0 for private trackers)
   - Seeding time ≥ minimum seed time (default: 48 hours)
4. **If all conditions met:** Delete torrent + data via `/api/v2/torrents/delete` with `deleteFiles=true`
5. **Private tracker handling:** Detects private flag in torrent properties; applies higher ratio threshold (5.0) and longer minimum seed time (7 days)
6. **Log every action** with timestamp, torrent name, ratio, and decision
7. **Sleep 30s** between batches to avoid overwhelming qBit

### Private vs Public Thresholds

| Parameter           | Public Tracker | Private Tracker |
|---------------------|----------------|-----------------|
| Target Ratio        | 3.0            | 5.0             |
| Min Seed Time       | 48 hours       | 7 days (168 hrs)|
| Delete Data         | Yes            | Yes             |

---

## Decluttarr

### Overview

Removes stalled, failed, or slow downloads from Sonarr/Radarr queues. Prevents queue clogging with dead torrents.

### Config

```
Location: /opt/decluttarr/config.yaml
```

### Configuration

```yaml
# /opt/decluttarr/config.yaml
decluttarr:
  general:
    timer: 60                    # Run every 60 seconds
    active_jobs:
      - remove_stalled_downloads
      - remove_slow_downloads
      - remove_failed_imports
      - remove_missing_files
      - remove_orphans
      - clean_banned_groups

  remove_stalled_downloads:
    enabled: true
    max_strikes: 3              # Remove after 3 consecutive stalled checks
    stalled_age_minutes: 120    # Must be in queue ≥ 2 hours
    remove_private: false       # Do not remove private tracker downloads
    remove_public: true

  remove_slow_downloads:
    enabled: true
    max_strikes: 5
    speed_threshold_kbps: 10    # Below 10 KB/s is "slow"
    slow_time_minutes: 60       # Must be slow for 1+ hour
    remove_private: false
    remove_public: true

  remove_failed_imports:
    enabled: true
    max_strikes: 1
    remove_private: true
    remove_public: true

  remove_missing_files:
    enabled: true
    max_strikes: 3
    remove_private: false
    remove_public: true

  remove_orphans:
    enabled: true
    max_strikes: 1
    remove_private: false
    remove_public: true

  clean_banned_groups:
    enabled: true
    max_strikes: 1
    banned_groups:
      - "YIFY"
      - "RARBG"
      - "x0r"

  connections:
    sonarr:
      url: "http://172.20.0.5:8989"
      api_key: "SONARR_API_KEY"
    radarr:
      url: "http://172.20.0.7:7878"
      api_key: "RADARR_API_KEY"
```

### Active Jobs

| Job                         | Description                                      | Max Strikes | Private |
|-----------------------------|--------------------------------------------------|-------------|---------|
| `remove_stalled_downloads`  | Torrents stuck with no progress ≥ 2 hours        | 3           | No      |
| `remove_slow_downloads`     | Torrents < 10 KB/s for ≥ 1 hour                  | 5           | No      |
| `remove_failed_imports`     | Completed but import errored                      | 1           | Yes     |
| `remove_missing_files`      | Files deleted from disk but still in queue        | 3           | No      |
| `remove_orphans`            | Queue item with no corresponding torrent          | 1           | No      |
| `clean_banned_groups`       | Releases from blacklisted groups                  | 1           | Both    |

---

## qBit Port Sync

### Overview

Updates qBittorrent's listening port when gluetun's forwarded port changes (VPN reconnection). Ensures P2P connectivity is maintained through the VPN tunnel.

### Service

```ini
# /etc/systemd/system/gluetun-qbit-sync.service
[Unit]
Description=Sync qBittorrent port from gluetun VPN
After=gluetun.service docker.service
Wants=gluetun.service
BindsTo=gluetun.service

[Service]
Type=simple
ExecStart=/opt/gluetun-qbit-sync.sh
Restart=always
RestartSec=30
User=root

[Install]
WantedBy=multi-user.target
```

### Script

```bash
#!/bin/bash
# /opt/gluetun-qbit-sync.sh
# Continuously monitors gluetun forwarded port and updates qBittorrent

QBIT_API="http://localhost:8083/api/v2"
QBIT_USER="topaz"
QBIT_PASS="USER_PASSWORD"
GLUETUN_CONTAINER="gluetun"

# Login and get cookie
COOKIE=$(curl -s -c - "${QBIT_API}/auth/login" \
    --data "username=${QBIT_USER}&password=${QBIT_PASS}" | grep SID | awk '{print $NF}')

while true; do
    # Try to get current container ID (handles restarts)
    CONTAINER_ID=$(docker ps -q --filter "name=${GLUETUN_CONTAINER}" 2>/dev/null)

    # Get forwarded port from gluetun control server
    PORT=$(curl -sf http://localhost:8000/v1/openvpn/portforwarded 2>/dev/null)

    if [ -n "$PORT" ] && [ "$PORT" != "$LAST_PORT" ]; then
        # Update qBit listening port
        curl -s "${QBIT_API}/app/setPreferences" \
            --data "json={\"listen_port\":${PORT}}" \
            --cookie "SID=${COOKIE}"

        LAST_PORT=$PORT
        echo "[$(date)] Port updated: $PORT"
    fi

    sleep 30
done
```

### Detection Logic

| Step | Action                                                    |
|------|-----------------------------------------------------------|
| 1    | Login to qBit API, get session cookie                     |
| 2    | Poll gluetun control server (`:8000/v1/openvpn/portforwarded`) |
| 3    | Compare with last known port (`$LAST_PORT`)                |
| 4    | If changed, POST new port to qBit preferences             |
| 5    | Handle container ID changes (docker restart detection)    |
| 6    | Sleep 30s, repeat                                         |

---

## Port Forwarding Auto-Detect


```bash
#!/bin/bash

set -e

MOONLIGHT_PORTS="47989:48010"
SSH_HOST_PORT=2225

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }


    | grep ipv4 | grep -v 'lo' | awk '{print $4}' | cut -d/ -f1 | head -1)

    exit 1
fi


# Save current Docker rules
DOCKER_RULE=$(iptables-save -t nat | grep "PREROUTING.*addrtype.*dst-type LOCAL.*DOCKER" || true)

# Clear existing forward rules (preserving Docker chains via iptables-save/restore approach)
iptables -t nat -F PREROUTING 2>/dev/null || true

# Restore critical Docker ADDRTYPE rule FIRST
iptables -t nat -A PREROUTING -m addrtype --dst-type LOCAL -j DOCKER


# SSH


# Persist rules
netfilter-persistent save

log "Port forwarding configured and saved."
```

### Detection Method

| Method              | Command                                   | Reliability |
|---------------------|-------------------------------------------|-------------|
| Fallback: ARP       | `arp -n \| grep virbr0`                    | Medium      |


```
```

---


### Scheduled Task

**Trigger:** At system startup
**Run As:** `SYSTEM` (highest privileges)
**Action:** Execute batch script

### gpu-fix.bat

```bat
@echo off

REM Force display detection (prevents "no display connected" issues)
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000" /v RMForceDisplay /t REG_DWORD /d 1 /f

reg add "HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000" /v DisableFeatureCheck /t REG_DWORD /d 1 /f

reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v FeatureScore /t REG_DWORD /d 0x1000 /f

```

### Registry Keys Applied

| Key Path                                                        | Value Name             | Type    | Data  | Purpose                              |
|-----------------------------------------------------------------|------------------------|---------|-------|--------------------------------------|
| `Control\GraphicsDrivers`                                       | `FeatureScore`         | DWORD   | 0x1000| Assign feature score for scheduling  |

---

## Laptop Health Monitor

### Cron

```cron
*/5 * * * * /tmp/health-check.sh >> /tmp/satellite-health.log 2>&1
```

### Script

```bash
#!/bin/bash
# /tmp/health-check.sh
# Laptop health monitoring: CPU temp, memory, disk, connectivity

echo "=== $(date) ==="

echo "CPU Temp:"
sensors 2>/dev/null | grep -E "Core|Package" || echo "sensors not available"

echo "Memory:"
free -h

echo "Disk:"
df -h / /home

echo "Network:"
ping -c 1 -W 2 10.0.0.1 >/dev/null 2>&1 && echo "Gateway: OK" || echo "Gateway: DOWN"

echo "Load:"
uptime

echo ""
```

### Log Rotation

```
Log file:    /tmp/satellite-health.log
Rotates:     Manually (tmpfs clears on reboot)
Max size:    ~10 MB per day
```

---

## PlexBot

### Service

```ini
# /etc/systemd/system/plexbot.service
[Unit]
Description=PlexBot Discord Bot
After=network.target docker.service
Wants=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/plexbot/bot.py
WorkingDirectory=/opt/plexbot
Restart=always
RestartSec=10
User=topaz
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

### Commands

| Command        | Description                                   | Access   |
|----------------|-----------------------------------------------|----------|
| `!status`      | Show Plex server status, stream count, uptime | Everyone |
| `!downloads`   | Show active qBit downloads (name, speed, ETA) | Everyone |
| `!ping`        | Bot latency check, server health              | Everyone |

### Behavior

- **on_ready:** Silent — no broadcast message on startup
- **Error handling:** Logs to `/opt/plexbot/bot.log`, auto-restarts via systemd
- **Permissions:** Read-only Plex + qBit API access

---


### Autostart

```
```

```ini
Type=Application
Comment=Restarts plasmashell if it crashes
Exec=/home/topaz/.local/bin/plasma-watchdog.sh
NoDisplay=true
```

### Script

```bash
#!/bin/bash
# ~/.local/bin/plasma-watchdog.sh
# Checks every 30s and restarts plasmashell if dead

while true; do
    if ! pgrep -x plasmashell > /dev/null; then
        echo "[$(date)] plasmashell dead, restarting..."
        kstart5 plasmashell &
    fi
    sleep 30
done
```

### Behavior Flow

```
Loop: Every 30 seconds
  ├── pgrep plasmashell
  ├── If NOT running → kstart5 plasmashell &
  └── Repeat
```

---

## Systemd Timers / Checks

### All Enabled Services

```bash

plexbot.service                loaded active running PlexBot Discord Bot
gluetun-qbit-sync.service      loaded active running Sync qBit port from gluetun VPN
qbit-watchdog.service          loaded active running qBittorrent Watchdog
fail2ban.service               loaded active running Fail2Ban
netfilter-persistent.service   loaded active exited  netfilter persistent configuration
```

### qbit-watchdog.service

```ini
[Unit]
Description=qBittorrent Watchdog
After=docker.service

[Service]
Type=simple
ExecStart=/opt/qbit-watchdog.sh
Restart=always
RestartSec=60
User=root
```

```bash
#!/bin/bash
# Checks qBit API health, restarts container if unresponsive

while true; do
    if ! curl -sf --max-time 10 http://localhost:8083/api/v2/app/version > /dev/null 2>&1; then
        echo "[$(date)] qBittorrent unresponsive, restarting..."
        docker restart qbittorrent
        sleep 30
    fi
    sleep 60
done
```

### fail2ban

```ini
# /etc/fail2ban/jail.local
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
```

---

## Automation Dependencies Graph

```
                    ┌───────────────┐
                    │  Host Boot    │
                    └───────┬───────┘
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
  ┌────▼─────┐      ┌──────▼──────┐      ┌──────▼──────┐
  │  starts  │      │   starts    │      │ persistent  │
  └────┬─────┘      └──────┬──────┘      └─────────────┘
       │                    │
  ┌────▼─────────┐   ┌─────▼──────────┐
  │ .service     │   │ + qBittorrent  │
  │   │          │   │ + media stack  │
  │   ▼          │   └────────┬───────┘
  │   .sh        │   ┌────────▼───────┐
  └──────────────┘   │ gluetun-qbit-  │
                      │ sync.service  │
                      └────────────────┘

  ┌──────────────┐    ┌──────────────┐
  │ plexbot      │    │ qbit-watchdog│
  │ .service     │    │ .service     │
  └──────────────┘    └──────────────┘

  ┌──────────────┐    ┌──────────────┐
  │ anti-seed    │    │ decluttarr   │
  │ (cron */2)   │    │ (cron/timer) │
  └──────────────┘    └──────────────┘
```
