# DATA FLOW — Complete Pipeline Diagram

```
                         REQUEST LAYER
 ┌───────────────┬────────────────┬───────────────────┐
 │  Overseerr    │  plexlist.txt  │  Discovery Engine  │
 │  (manual)     │  (curation)    │  (automatic, 2am)  │
 └───────┬───────┴────────┬───────┴─────────┬─────────┘
         │                │                 │
         └────────────────┼─────────────────┘
                          │
              ┌───────────▼───────────┐
              │  Radarr / Sonarr      │
              │  2,174 movies         │
              │  200 shows            │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │  Prowlarr             │
              │  10 indexers          │
              │  + FlareSolverr       │
              └───────────┬───────────┘
                          │
              ╔═══════════▼═══════════╗
              ║    DOWNLOAD LAYER     ║
              ║                      ║
              ║  LAPTOP <laptop-ip>   ║
              ║  ┌────────────────┐  ║
              ║  │ gluetun (VPN)  │  ║
              ║  │ AirVPN WG      │  ║
              ║  │ FIREWALL=on    │  ║
              ║  │ ┌────────────┐ │  ║
              ║  │ │ qBittorrent│ │  ║
              ║  │ │ DL:15      │ │  ║
              ║  │ │ Tor:200    │ │  ║
              ║  │ └─────┬──────┘ │  ║
              ║  └───────┼────────┘  ║
              ╚══════════╪═══════════╝
                         │ NFS write
              ┌──────────▼──────────┐
              │ SERVER /mnt/20TB/   │
              │ homelab/media/      │
              │ downloads/          │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │   IMPORT LAYER       │
              │                      │
              │ Radarr/Sonarr poll   │
              │ qBit API (~1 min)    │
              │ ↓                    │
              │ Import to media:     │
              │  Movies → /mnt/      │
              │  20TB/Movies 1/      │
              │  TV → /mnt/20TB/     │
              │  TV Shows 1/         │
              │ ↓                    │
              │ Remove from qBit     │
              │ (deleteFiles=false)  │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │   MEDIA LAYER        │
              │                      │
              │  ┌────────────────┐  │
              │  │ Plex           │  │
              │  │ 593 movies     │  │
              │  │ 465 shows      │  │
              │  │ GPU NVENC      │  │
              │  └────────────────┘  │
              │  ┌────────────────┐  │
              │  │ tdarr          │  │
              │  │ HEVC encode    │  │
              │  │ (midnight-10a) │  │
              │  └────────────────┘  │
              │  ┌────────────────┐  │
              │  │ Bazarr         │  │
              │  │ subtitles      │  │
              │  └────────────────┘  │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │   STREAM LAYER       │
              │                      │
              │ Remote: port 32400   │
              │ → Plex               │
              │ → GPU transcode      │
              │ → Direct play        │
              │                      │
              │ Users: topazconch    │
              │        astrotopaz    │
              └──────────────────────┘


                    AUTOMATION LAYER (22 timers)

  torrent-doctor(10m) ──→ Inject 37 trackers, recheck stalled
  tdarr-post(5m) ──→ Delete originals after encoding
  smart-fill(30m) ──→ Add missing eps when qBit <150
  balance-8tb(30m) ──→ Move 8TB→20TB at 85%
  complete-media(6h) ──→ Find all gaps (seasons, eps, sequels)
  auto-dedup(6h) ──→ Remove duplicates safely
  discovery(2am) ──→ TMDB scan + scoring + plexlist
  nightly-backup(3am) ──→ Export all to desktop
  taste-daily(2:30am) ──→ Update watch counts + genres
  taste-weekly(Sun) ──→ Director/actor affinity
  health-score(30m) ──→ HEALTH_SCORE.json
  pipeline-gc(4am) ──→ Clean up candidates, logs
  vpn-watchdog(60s) ──→ Restart gluetun if dead
  cleanup-completed(5m) ──→ Remove torrents after import
```
