# API Reference — Keys, Tokens & Credentials

> **WARNING:** This file contains secrets. Do not commit to version control. Keep file permissions restricted.

---

## Media Stack

### Sonarr

| Field | Value |
|-------|-------|
| URL | `http://10.0.0.200:8989` |
| API Key | `SONARR_API_KEY` |
| API Base | `/api/v3` |

```bash
# Test
curl -s "http://10.0.0.200:8989/api/v3/system/status?apikey=SONARR_API_KEY"
```

### Radarr

| Field | Value |
|-------|-------|
| URL | `http://10.0.0.200:7878` |
| API Key | `RADARR_API_KEY` |
| API Base | `/api/v3` |

```bash
# Test
curl -s "http://10.0.0.200:7878/api/v3/system/status?apikey=RADARR_API_KEY"
```

### Prowlarr

| Field | Value |
|-------|-------|
| URL | `http://10.0.0.200:9696` |
| API Key | `PROWLARR_API_KEY` |
| API Base | `/api/v1` |

```bash
# Test
curl -s "http://10.0.0.200:9696/api/v1/system/status?apikey=PROWLARR_API_KEY"
```

### qBittorrent

| Field | Value |
|-------|-------|
| URL | `http://10.0.0.200:8081` |
| Username | `topaz` |
| Password | `USER_PASSWORD` |
| API Base | `/api/v2` |

```bash
# Login + get SID cookie
curl -s -c /tmp/qbit.cookie \
  --data "username=topaz&password=USER_PASSWORD" \
  "http://10.0.0.200:8081/api/v2/auth/login"

# Get transfer info
curl -s -b /tmp/qbit.cookie \
  "http://10.0.0.200:8081/api/v2/transfer/info"
```

---

## Plex

| Field | Value |
|-------|-------|
| URL | `http://10.0.0.200:32400` |
| Token | `PLEX_TOKEN` |
| Token source | `/etc/pipeline/config.json` |

### Token Refresh

If the token needs updating:

1. Sign in at `https://app.plex.tv`
2. Inspect any API request → look for `X-Plex-Token` header
3. Update both:
   - `/etc/pipeline/config.json`
   - This document

```bash
# Test
curl -s "http://10.0.0.200:32400/?X-Plex-Token=PLEX_TOKEN"
```

---

## Discord (PlexBot)

| Field | Value |
|-------|-------|
| Bot token | In `/etc/pipeline/config.json` (field: `discord_token`) |
| Webhook URL | In `/etc/pipeline/config.json` (field: `discord_webhook`) |

```bash
# Extract token
jq -r '.discord_token' /etc/pipeline/config.json
```

---

## TMDB (The Movie Database)

| Field | Value |
|-------|-------|
| API Key (v3) | `5e00e3a8059e33e9f559bf884ed726ed` |
| API Base | `https://api.themoviedb.org/3` |

Used by: **Sonarr**, **Radarr**, **Overseerr** for metadata and artwork.

```bash
# Test
curl -s "https://api.themoviedb.org/3/movie/550?api_key=5e00e3a8059e33e9f559bf884ed726ed"
```

---

## Decluttarr

| Field | Value |
|-------|-------|
| Config file | `/mnt/20TB/homelab/media/compose/decluttarr/config.yaml` |

### Credentials (embedded in config)

| Service | Credential |
|---------|------------|
| Sonarr API Key | `SONARR_API_KEY` |
| Radarr API Key | `RADARR_API_KEY` |
| qBittorrent User | `topaz` |
| qBittorrent Pass | `USER_PASSWORD` |

---

## System Credentials

All systems share the same primary credential pair:

| System | Username | Password | SSH Port |
|--------|----------|----------|----------|
| Laptop (Ubuntu) | `laptop` | `USER_PASSWORD` | `2225` |

### Quick SSH

```bash
# Server
ssh -p 2223 topaz@10.0.0.200

# Laptop
ssh -p 2225 laptop@10.0.0.234

ssh -p 2225 topaz@10.0.0.200
```

---

## Centralized Config File

All secrets and environment variables are consolidated in:

```
/etc/pipeline/config.json
```

### Schema (partial)

```json
{
  "plex_token": "PLEX_TOKEN",
  "discord_token": "XXXXXXXXXX",
  "discord_webhook": "https://discord.com/api/webhooks/...",
  "tmdb_key": "5e00e3a8059e33e9f559bf884ed726ed",
  "sonarr": {
    "url": "http://10.0.0.200:8989",
    "api_key": "SONARR_API_KEY"
  },
  "radarr": {
    "url": "http://10.0.0.200:7878",
    "api_key": "RADARR_API_KEY"
  },
  "prowlarr": {
    "url": "http://10.0.0.200:9696",
    "api_key": "PROWLARR_API_KEY"
  },
  "qbittorrent": {
    "url": "http://10.0.0.200:8081",
    "username": "topaz",
    "password": "USER_PASSWORD"
  }
}
```

### Permissions

```bash
sudo chmod 600 /etc/pipeline/config.json
sudo chown root:root /etc/pipeline/config.json
```

---

## API Quick Test (All Services)

```bash
#!/bin/bash
# Quick smoke test of all API endpoints
curl -s -o /dev/null -w "Sonarr:    %{http_code}\n" "http://10.0.0.200:8989/api/v3/system/status?apikey=SONARR_API_KEY"
curl -s -o /dev/null -w "Radarr:    %{http_code}\n" "http://10.0.0.200:7878/api/v3/system/status?apikey=RADARR_API_KEY"
curl -s -o /dev/null -w "Prowlarr:  %{http_code}\n" "http://10.0.0.200:9696/api/v1/system/status?apikey=PROWLARR_API_KEY"
curl -s -o /dev/null -w "qBit:      %{http_code}\n" "http://10.0.0.200:8081/api/v2/app/version"
curl -s -o /dev/null -w "Plex:      %{http_code}\n" "http://10.0.0.200:32400/identity"
curl -s -o /dev/null -w "TMDB:      %{http_code}\n" "https://api.themoviedb.org/3/configuration?api_key=5e00e3a8059e33e9f559bf884ed726ed"
```

Save as `/tmp/api-smoke.sh` on server, `chmod +x`, run anytime for a full health sweep.
