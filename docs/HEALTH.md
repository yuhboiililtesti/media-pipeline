# Health Monitoring & Scanning

## Server Health Scan

### Overview

| Field | Value |
|-------|-------|
| Script | `/opt/server-health-scan.sh` |
| Sections | 14 |
| Runtime | ~30 seconds |
| Requires | root (for certain checks) |
| Output | Terminal (stdout) — copy/paste into analysis |

### Sections Covered

| # | Section | Checks Performed |
|---|---------|-----------------|
| 1 | System | Uptime, load average, memory usage (`free -h`), kernel version (`uname -r`) |
| 3 | Network | `ip addr`, bridge state (`br0`), listening ports (`ss -tlnp`), IP forwarding status, ARP table |
| 4 | DNS | Pi-hole status (`pihole status`), DNS resolution tests (internal + external), ad blocking rate |
| 5 | Authentication | Last 10 logins (`last -10`), SSH brute-force attempts (fail2ban), sudo log |
| 6 | Docker | `docker ps -a` (all containers, including stopped), Docker disk usage, Docker version |
| 7 | Processes | Top 10 by CPU, top 10 by memory, zombie count, total process count |
| 8 | Persistence | systemd enabled units, cron jobs (all users), `/etc/rc.local`, autostart entries |
| 10 | Filesystem | `df -h` across all mounts, inode usage, `/mnt/20TB` available space, decluttarr cache size |
| 11 | Firewall | `iptables -L -n` summary, active rules count, forwarded ports (2223, 2225, 32400 etc.), rate-limiting rules |
| 14 | Integrity | Plex token validity test, config.json checksum, key file hashes compared to stored baseline |

### Run

```bash
# From server terminal or SSH

# Or directly
sudo /opt/server-health-scan.sh
```

---

## Windows Security Scan

### Overview

| Field | Value |
|-------|-------|
| Script | `C:\Windows\Temp\security-scan.ps1` |
| Sections | 12 |
| Runtime | ~45 seconds |
| Requires | Administrator PowerShell |
| Output | Console |

### Sections Covered

| # | Section | Checks Performed |
|---|---------|-----------------|
| 1 | System | OS version, build, hostname, uptime, timezone, last boot |
| 2 | Network | `netstat -ano` listening ports, active TCP connections, `Get-NetConnectionProfile` firewall profiles |
| 3 | DNS | Resolution tests against Pi-hole, public DNS fallback test |
| 4 | Processes | Running process list, CPU/memory top 10, unsigned binaries |
| 5 | Persistence | Registry Run/RunOnce keys, Startup folder, scheduled tasks, services set to auto-start |
| 6 | Tasks | All scheduled tasks, last run time, result codes, trigger types |
| 7 | Accounts | Local user list, admin group membership, guest status, last password change |
| 9 | Defender | Real-time protection status, last scan time, exclusions list, threat history |
| 10 | Installed Software | All entries from `Get-WmiObject Win32_Product`, version numbers, install dates |
| 11 | Events | Security log (last 24h — EventID 4624/4625/4672), System log errors/warnings |

### Run

```bash
# From server SSH

# From Windows directly (Run as Administrator)
powershell -ExecutionPolicy Bypass -File "C:\Windows\Temp\security-scan.ps1"
```

---

## Uptime Kuma Monitoring

Runs on **laptop** (`10.0.0.234:3001`).

### HTTP Monitors (60s Interval)

| # | Monitor | URL | Expected | Alert On |
|---|---------|-----|----------|----------|
| 1 | Sonarr | `http://10.0.0.200:8989` | 200 | Down ≥ 2 min |
| 2 | Radarr | `http://10.0.0.200:7878` | 200 | Down ≥ 2 min |
| 3 | Prowlarr | `http://10.0.0.200:9696` | 200 | Down ≥ 2 min |
| 4 | qBittorrent | `http://10.0.0.200:8081` | 200 | Down ≥ 2 min |
| 5 | Tdarr | `http://10.0.0.200:8265` | 200 | Down ≥ 2 min |
| 6 | Overseerr | `http://10.0.0.200:5055` | 200 | Down ≥ 2 min |
| 7 | Plex | `http://10.0.0.200:32400/web` | 200 | Down ≥ 2 min |
| 8 | Immich | `http://10.0.0.200:2283` | 200 | Down ≥ 2 min |

### TCP Monitor (20s Interval)

| # | Monitor | Host:Port | Purpose | Alert On |
|---|---------|-----------|---------|----------|

### Ping Monitors (60s Interval)

| # | Monitor | Target | Alert On |
|---|---------|--------|----------|
| 1 | Server | `10.0.0.200` | Packet loss ≥ 50% |
| 2 | Gateway | `10.0.0.1` | Down ≥ 2 min |
| 3 | DNS (Pi-hole) | `10.0.0.200` | Down ≥ 2 min |

### Self Check

| # | Monitor | Type | Interval | Alert On |
|---|---------|------|----------|----------|
| 1 | Kuma | HTTP `localhost:3001` | 60s | Down (immediate) |

### Alerting

All monitors send alerts to a Discord channel via the PlexBot webhook when a service goes down and again when it recovers.

---

## Laptop Health Monitor

### Overview

| Field | Value |
|-------|-------|
| Script | `/tmp/health-check.sh` |
| Cron | `*/5 * * * *` |
| Log | `/var/log/laptop-health.log` |
| User | `laptop` (user crontab) |

### Checks Performed

| # | Target | Method | Alert Threshold |
|---|--------|--------|-----------------|
| 1 | Uptime | `uptime` | — (info only) |
| 2 | CPU Load | `/proc/loadavg` | > core count |
| 3 | Memory | `free -m` | < 500 MB available |
| 4 | Disk | `df -h /` | > 85% used |
| 5 | Docker | `docker ps -q \| wc -l` | < 2 containers |
| 6 | Uptime Kuma | `curl localhost:3001` | non-200 |
| 7 | Heimdall | `curl localhost:8080` | non-200 |
| 8 | Internet | `ping 1.1.1.1` | 100% loss |
| 9 | Server Ping | `ping 10.0.0.200` | 100% loss |
| 10 | DNS | `nslookup google.com` | resolution failure |

### View Log

```bash
ssh -p 2225 laptop@10.0.0.234 'tail -50 /var/log/laptop-health.log'
```

---

## Manual Health Checks

Quick commands for targeted troubleshooting. Run on the **server** unless noted otherwise.

### System Resources

```bash
free -h                    # Memory usage
df -h /mnt/20TB            # Storage array
uptime                     # Load + uptime
htop                       # Interactive process monitor
```

### Docker

```bash
docker ps -a               # All containers (status)
docker stats --no-stream   # Resource usage per container
docker system df           # Docker disk usage
docker logs sonarr --tail 50
```

### Virtualization

```bash
virsh domstate win10       # Running / shut off
```


```bash
```

### Web UI Quick Checks

```bash
curl -s -o /dev/null -w "%{http_code}" http://10.0.0.200:8989   # Sonarr
curl -s -o /dev/null -w "%{http_code}" http://10.0.0.200:7878   # Radarr
curl -s -o /dev/null -w "%{http_code}" http://10.0.0.200:9696   # Prowlarr
curl -s -o /dev/null -w "%{http_code}" http://10.0.0.200:8081   # qBit
curl -s -o /dev/null -w "%{http_code}" http://10.0.0.200:8265   # Tdarr
curl -s -o /dev/null -w "%{http_code}" http://10.0.0.200:5055   # Overseerr
curl -s -o /dev/null -w "%{http_code}" http://10.0.0.200:32400/web  # Plex
curl -s -o /dev/null -w "%{http_code}" http://10.0.0.200:2283   # Immich
curl -s -o /dev/null -w "%{http_code}" http://10.0.0.234:3001   # Kuma
curl -s -o /dev/null -w "%{http_code}" http://10.0.0.234:8080   # Heimdall
```

### qBit Transfer Info

```bash
# Login
curl -s -c /tmp/qbit.cookie \
  --data "username=topaz&password=USER_PASSWORD" \
  "http://10.0.0.200:8081/api/v2/auth/login"

# Transfer info
curl -s -b /tmp/qbit.cookie "http://10.0.0.200:8081/api/v2/transfer/info"

# List torrents (filter active)
curl -s -b /tmp/qbit.cookie \
  "http://10.0.0.200:8081/api/v2/torrents/info?filter=active"
```

### SSH Connectivity

```bash
ssh -p 2223 topaz@10.0.0.200 echo ok           # Server
ssh -p 2225 laptop@10.0.0.234 echo ok           # Laptop
```

### Firewall Review

```bash
sudo iptables -L -n -v | grep -E "dpt:2223|dpt:2225|dpt:47989|dpt:32400"
sudo fail2ban-client status sshd
```

---

## Health Check Automation Chain

```
Laptop (health-check.sh, cron every 5min)
  │
  ├── Checks: self (docker, disk, memory)
  ├── Pings: server (10.0.0.200), internet
  │
  └── Uptime Kuma (every 20s—60s)
       ├── HTTP checks: Sonarr, Radarr, Prowlarr, qBit, Tdarr, Overseerr, Plex, Immich
       └── Alerts: Discord (PlexBot webhook)
  
  │
  └── health-scan.sh (14 sections)
       └── Output: terminal

  │
  └── security-scan.ps1 (12 sections)
       ├── System, Network, Processes, Persistence, Tasks, Defender, Events, Integrity
       └── Output: terminal
```
