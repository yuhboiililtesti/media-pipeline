# Laptop — Monitoring & Configuration

## Hardware

| Field | Value |
|-------|-------|
| Model | Lenovo ThinkPad SL510 |
| OS | Ubuntu Server (LTS) |
| IP | `10.0.0.234` (static DHCP reservation) |
| SSH Port | `2225` |
| User | `laptop` |
| Role | Monitoring & dashboard host |

---

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| Uptime Kuma | `uptime-kuma` | `3001` | Status monitoring & alerts |
| Heimdall | `heimdall` | `8080` | Dashboard / application launcher |

### Access

| Service | URL |
|---------|-----|
| Uptime Kuma | `http://10.0.0.234:3001` |
| Heimdall | `http://10.0.0.234:8080` |

---

## Uptime Kuma Monitors

All monitors run 24/7 with alerting via Discord (PlexBot webhook).

### HTTP Monitors (60s interval)

| Monitor | URL | Expected Code | Purpose |
|---------|-----|---------------|---------|
| Sonarr | `http://10.0.0.200:8989` | 200 | TV series management |
| Radarr | `http://10.0.0.200:7878` | 200 | Movie management |
| Prowlarr | `http://10.0.0.200:9696` | 200 | Indexer proxy |
| qBittorrent | `http://10.0.0.200:8081` | 200 | Torrent client |
| Tdarr | `http://10.0.0.200:8265` | 200 | Media transcoding |
| Overseerr | `http://10.0.0.200:5055` | 200 | Request management |
| Plex | `http://10.0.0.200:32400/web` | 200 | Media server |
| Immich | `http://10.0.0.200:2283` | 200 | Photo backup |

### TCP Monitor (20s interval)

| Monitor | Host | Port | Purpose |
|---------|------|------|---------|

### Ping Monitors (60s interval)

| Monitor | Target | Purpose |
|---------|--------|---------|
| Server | `10.0.0.200` | Host connectivity |
| Gateway | `10.0.0.1` | Router/gateway |
| DNS (Pi-hole) | `10.0.0.200` | DNS server |

### Self Check

| Monitor | Type | Interval |
|---------|------|----------|
| Kuma Self | HTTP GET `http://localhost:3001` | 60s |

### Typical Uptime Percentages

| Service | 30-day avg |
|---------|------------|
| Server | 99.8% |
| Plex | 99.7% |
| Sonarr | 99.9% |
| Radarr | 99.9% |
| qBittorrent | 99.8% |
| Gateway | 99.9% |
| DNS | 99.9% |

---

## Health Monitor

### Script

```
/tmp/health-check.sh
```

### Cron Entry

```cron
*/5 * * * * /tmp/health-check.sh >> /var/log/laptop-health.log 2>&1
```

### What It Checks

| # | Check | Details |
|---|-------|---------|
| 1 | System uptime | `uptime` output |
| 2 | CPU load | 1 / 5 / 15 min load averages |
| 3 | Memory | `free -h` — warn if < 500 MB available |
| 4 | Disk usage | `df -h /` — warn if > 85% |
| 5 | Docker status | `docker ps` — count running containers |
| 6 | Uptime Kuma reachable | `curl -s -o /dev/null -w "%{http_code}" http://localhost:3001` |
| 7 | Heimdall reachable | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080` |
| 8 | Internet access | `ping -c 2 1.1.1.1` |
| 9 | Server reachable | `ping -c 2 10.0.0.200` |
| 10 | DNS resolution | `nslookup google.com 10.0.0.200` |

### Log Location

```
/var/log/laptop-health.log
```

### Full Script

```bash
#!/bin/bash
LOG="/var/log/laptop-health.log"
echo "=== $(date) ===" >> "$LOG"

# 1. Uptime
echo "UPTIME: $(uptime)" >> "$LOG"

# 2. CPU load
echo "CPU: $(cat /proc/loadavg)" >> "$LOG"

# 3. Memory
MEM_AVAIL=$(free -m | awk '/Mem:/ {print $7}')
echo "MEMORY: ${MEM_AVAIL}MB available" >> "$LOG"
[ "$MEM_AVAIL" -lt 500 ] && echo "WARNING: Low memory!" >> "$LOG"

# 4. Disk
DISK_PCT=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
echo "DISK: ${DISK_PCT}% used on /" >> "$LOG"
[ "$DISK_PCT" -gt 85 ] && echo "WARNING: Disk usage high!" >> "$LOG"

# 5. Docker
CONTAINERS=$(docker ps -q | wc -l)
echo "DOCKER: ${CONTAINERS} containers running" >> "$LOG"
[ "$CONTAINERS" -lt 2 ] && echo "WARNING: Docker containers missing!" >> "$LOG"

# 6. Uptime Kuma
KUMA_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:3001)
echo "KUMA: HTTP ${KUMA_CODE}" >> "$LOG"

# 7. Heimdall
HEIM_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:8080)
echo "HEIMDALL: HTTP ${HEIM_CODE}" >> "$LOG"

# 8. Internet
ping -c 2 -W 3 1.1.1.1 > /dev/null 2>&1 && echo "INTERNET: OK" >> "$LOG" || echo "WARNING: Internet down!" >> "$LOG"

# 9. Server
ping -c 2 -W 3 10.0.0.200 > /dev/null 2>&1 && echo "SERVER: OK" >> "$LOG" || echo "WARNING: Server unreachable!" >> "$LOG"

# 10. DNS
nslookup google.com 10.0.0.200 > /dev/null 2>&1 && echo "DNS: OK" >> "$LOG" || echo "WARNING: DNS failure!" >> "$LOG"

echo "" >> "$LOG"
```

---

## Access

### URLs

| Service | URL |
|---------|-----|
| Uptime Kuma | `http://10.0.0.234:3001` |
| Heimdall | `http://10.0.0.234:8080` |

### SSH

```bash
# Direct (local network)
ssh -p 2225 laptop@10.0.0.234

# From server
ssh -p 2225 laptop@10.0.0.234
```

---

## Fail2ban Whitelist

The laptop IP (`10.0.0.234`) is **whitelisted** on the server's Fail2ban configuration to prevent the health-check traffic from triggering SSH ban rules.

### Server-side Configuration

In `/etc/fail2ban/jail.local`:

```ini
[DEFAULT]
ignoreip = 127.0.0.1/8 10.0.0.0/24 10.0.0.234
```

> Without this whitelist, the laptop's frequent curl/ping checks (health-check.sh every 5 min) could accumulate enough "failed" auth attempts from port-scan-like behavior to trigger a temporary ban on the laptop IP.

### Verify

```bash
# On server
sudo fail2ban-client status sshd
sudo fail2ban-client get sshd ignoreip
```

---

## Quick Reference

| Task | Command |
|------|---------|
| View health log | `tail -f /var/log/laptop-health.log` |
| Container status | `docker ps` |
| Restart Uptime Kuma | `docker restart uptime-kuma` |
| Restart Heimdall | `docker restart heimdall` |
| Reboot laptop | `sudo reboot` |
| Check disk | `df -h` |
| Check memory | `free -h` |
