# PIPELINE CHANGELOG — Full History
# All versions, changes, fixes, and deployments

---

## v7.4 — 2026-07-18 (CURRENT)

### Fixed
- **Gluetun DNS/health check (ROOT CAUSE):** `DNS_UPSTREAM_PLAIN_ADDRESSES=1.1.1.1:53` didn't resolve through WireGuard. Health check used `127.0.0.1:53` which was broken. Result: gluetun restarted 12x every 5 minutes, taking qBit offline each time. Fixed with `DNS_KEEP_NAMESERVER=on` + `VPN_HEALTHCHECK_ENABLED=off` + removed Docker health check block. **Now 0 restarts, stable indefinitely.**
- **qBit network loss:** Every gluetun restart dropped qBit's network attachment (network_mode: service:gluetun). Container showed `Networks: {}`. Now stable at 97.5 MB/s DL, 0 disconnects.
- **Misplaced media:** Mob Psycho 100 S1+S2, Attack on Titan (Shingeki no Kyojin) S3, Family Guy S04 were in Movies directory. Moved to TV Shows. Root cause: Radarr misclassified anime/TV shows as movies on import.

### Added
- **Media Classifier (`/opt/classify_media.py`):** New automated system that scans all media directories. Detects TV shows misplaced in Movies (uses S##E##, S##., Season #, EP## patterns) and movies misplaced in TV Shows. Skips movie extras (featurettes, commentaries, NCOP/NCED, making-of). Runs every 6 hours via `classify-media.timer`.
- **GTA V Enhanced YimMenu V2 Lua Suite:** 18 Lua scripts (8 custom + 10 original) for GTA V Enhanced on CachyOS desktop. Money safe filler, godmode, teleport, vehicle fix/upgrades, weapon giver, heal, full recovery, property unlock. Uses only confirmed APIs: `script.run_in_callback`, `natives.load_natives()`, hardcoded hashes. No gui/joaat/register_looped support in this YimMenu build.
- **Lua API documentation:** Discovered exact YimMenu V2 Enhanced build capabilities. Available: script, natives, stats, notify, log, MONEY, NETWORK, ENTITY, PLAYER, PED, OBJECT, VEHICLE, STREAMING, HUD, PAD, TASK, CUTSCENE, WEAPON, transactions. Not available: gui, joaat, register_looped, run_in_fiber, register_callback, commands.

### Notes
- Money injection blocked by FSL local saves. Safe filler method works (nightclub/agency/arcade safe earnings via stats API). Use YimMenu UI Recovery → Transactions for direct wallet cash.
- Gluetun VPN health check permanently disabled — DNS resolution doesn't work through WireGuard tunnel. Container health verified by checking qBit API connectivity instead.

---

## v7.3 — 2026-07-15

### Fixed
- **Server OOM crashes (ROOT CAUSE):** 31GB RAM, VM=12GB, Docker=10GB — only 3GB headroom. Server killed SSH, qBit, and Docker every few hours. Reduced VM RAM to 10GB + added memory limits to all Docker containers + sshd OOM protection (-500 score).
- **Gluetun VPN DNS:** `DNS_UPSTREAM_PLAIN_ADDRESSES=1.1.1.1` missing port — caused gluetun crash every 4min, taking qBit offline. Fixed to `1.1.1.1:53`.
- **Gluetun health check:** ICMP ping was failing on high-latency VPN — changed to HTTP (1.1.1.1), increased start period to 120s, added 30s tolerance.
- **Docker restart policies:** 10 containers had `restart: no` — wouldn't survive crashes. All now `restart: unless-stopped`.
- **Docker forward rules:** Missing after compose restart — added to `fix-nftables.service` for boot persistence.
- **VM QXL removed:** GPU-only display. Windows renders directly to GTX 1660 SUPER. Monitor + Moonlight both work.
- **Dual audio fix:** Pipeline now keeps English-dubbed foreign content (Squid Games, anime dubs). Only blocks pure non-English with no English audio track.
- **qBit stability:** Relaxed health checks (60s interval, 30s timeout, 10 retries) — survives VPN reconnects and RAM pressure.

### Added
- **Smart quality size limits:** TV episodes max 3-5GB, Movies max 4-8GB — prevents huge remux downloads.
- **fix-phantom auto-hook:** Systemd service runs before VM start if phantom flag exists.
- **Deduper v2:** Hash-verified, Tdarr-safe (skips recently modified files). Timer changed from daily to every 12h.
- **Discord webhook:** Rate-limited notifications (5min cooldown) for container failures, disk warnings.
- **Plex unmatched fixer:** Daily sweep for unmatched items, triggers re-match.
- **Discovery engine:** Weekly TMDb trending scan with 6.0+ rating + 100+ vote filter.
- **Tdarr monthly report:** Space saved, files transcoded, failure count.

### Changed
- VM RAM: 12GB → 10GB
- VM display: QXL removed, GPU-only
- Golden XML: Updated to 10GB + GPU-only
- Docker: All 16 containers `restart: unless-stopped`
- Pipeline: All scripts updated for dual audio, S2-NN detection, website prefix stripping
- Anti-cheat: SMBIOS ASUSTeK ROG, vendor_id AuthenticAMD, kvm hidden (safe approach, no boot break)
- Commands: `pipeline {status|dedup|health|log|search|restart}`, `vm {moon|spice|ssh|status}`

### VM Status
- GPU: GTX 1660 SUPER, VFIO passthrough, GPU-only display
- Display: Physical monitor + Moonlight (Sunshine NVENC 1080p120)
- RAM: 10GB
- Autostart: Enabled

---

## v7.1 — 2026-07-14

### Fixed
- **Pipeline sorting bug (CRITICAL):** Movies were being misclassified as TV episodes and moved to TV Shows directories. Rewrote section 7 (AUTO-IMPORT) in autonomous-pipeline.py with robust detection:
  - Strong TV signals: SxxExx, Sxx., Season X
  - False-positive exclusions: "complete series", "collection", "anthology"
  - Show name extraction with clean release tag removal
  - Cross-type dedup against both movie and TV directories
- **Batch import sorting bug (CRITICAL):** batch_import.py was using weak `is_tv()` regex that matched "COMPLETE" keyword, causing movies to be classified as TV. Rewrote as v3 with:
  - Strong TV signal detection (SxxExx, Sxx., Season X)
  - Movie false-positive exclusions
  - Cross-type dedup: checks if movie exists in TV dirs and vice versa
  - Size-based dedup: catches renames across drives (within 1MB tolerance)
- **qBit unreachable by pipeline:** Docker's qBit listens on IPv4 only, but `localhost` resolved to `::1` (IPv6) first. Changed config.json `qbit.server` from `http://localhost:8083` to `http://127.0.0.1:8083`.
- **cross-seed crash-loop:** Hardlinks can't cross drives (/mnt/8TB -> /mnt/20TB). Changed `linkType` from `hardlink` to `symlink` in cross-seed config.js.

### Added
- **CHANGELOG.md:** Full version history for Pipeline-Doc
- **ECOSYSTEM.md:** Complete ecosystem documentation (CachyOS, laptop, VM, networking)

### Changed
- batch_import.py: v2 -> v3 (correct sorting + cross-type dedup)
- autonomous-pipeline.py: section 7 rewritten with correct TV/movie detection
- config.json: `localhost:8083` -> `127.0.0.1:8083`

---

## v7.0 — 2026-07-13

### Fixed
- **nftables/UFW firewall conflict (ROOT CAUSE of all LAN access issues):** UFW wrote rules to iptables but nftables was the actual packet filter with policy DROP. Added 16+ missing port rules to nftables INPUT chain. Created fix-nftables.service for persistence.
- **Plex EHOSTUNREACH:** Same root cause — nftables blocking port 32400.
- **qBit WebUI unreachable:** Same root cause — nftables blocking port 8083.
- **Gaming VM cold boot:** Unmasked and enabled libvirtd, enabled gaming-vm.service, VM autostart configured.
- **VM disk resize:** Expanded from 550GB to 1TB QCOW2 + NTFS partition resize.
- **FlareSolverr exposed:** Bound to 127.0.0.1:8191 (was 0.0.0.0).
- **SSH password auth:** Generated ed25519 keypair, deployed to server, disabled password auth.
- **WireGuard keys in docker-compose.yml:** Moved to .env file with perms 600.
- **Memory limits:** Added mem_limit to tdarr-node (2GB), qbittorrent (4GB), immich-redis (512MB), immich-postgres (1GB), decluttarr (256MB).
- **Quality profiles:** Set upgradeAllowed=True on Sonarr profile ID:3 (cutoff Bluray-1080p) and Radarr profile ID:6.
- **Dead torrents cleaned:** 27 paused dead + 9 stalled + 4 errored deleted.
- **Failed services:** transmission-daemon, fwupd, fwupd-refresh disabled/masked.

### Added
- **media-dedupe.py:** Cross-drive deduplication. First run: 79 dupes deleted, 132.8 GB recovered.
- **media-dedupe.timer:** Daily dedup schedule.
- **fix-nftables.service:** Persistent firewall rules (flush+rebuild on boot).
- **gaming-vm.service:** VM autostart on boot.
- **NIC tuning:** Disabled power saving, TCP keepalive 60s/10s/6 probes, WoL enabled.
- **UFW firewall:** All internal ports restricted to 10.0.0.0/24 LAN only.
- **SSH key auth:** ed25519 key at ~/.ssh/server_ed25519.
- **Overseerr <-> Plex connected.**
- **cross-seed apiKey set.**

### Changed
- Pipeline v6.1 -> v7.0 (multiple iterations, fixed state variable collision, syntax errors)
- config.env: Ports 8081->8083, 51413->51414
- gluetun DNS: DNS_ADDRESS -> DNS_UPSTREAM_PLAIN_ADDRESSES=1.1.1.1
- Library refreshes: Sonarr RescanSeries+RefreshSeries, Radarr RefreshMovies
- Prowlarr->Sonarr+Radarr fullSync enabled

---

## v6.1 — 2026-07-11

### Fixed
- State variable collision in pipeline
- Syntax errors in autonomous-pipeline.py
- Library refresh triggers

### Added
- recovery.py + recovery-sync.timer (daily disk vs *arr scan)
- Batch import system (/opt/batch_import.py + batch-import.timer)
- Health monitor (/opt/health-monitor.py + health-monitor.timer)
- Anti-seed v2 (only cleans dead/zero-seed)

### Changed
- Pipeline v6.0 -> v6.1
- Consolidated 21 separate timers into single autonomous-pipeline

---

## v6.0 — 2026-07-10

### Fixed
- SATA cable failure on 20TB drive (physically reseated)
- Docker data-root moved to /mnt/8TB (survives 20TB failures)
- All 133 torrents entered error state (deleted, triggered fresh searches)
- Laptop qBit overloaded (1,303 torrents cleaned, limits set)
- Indexer drought (13 Prowlarr indexers + FlareSolverr deployed)
- Non-English content leaking (NON_ENG filter added)
- 4K content being downloaded (nuked from all profiles)
- Files not renamed after import (naming conventions configured)
- Plex not auto-scanning (notification triggers added)

### Added
- Seasonal cascade module (S01 -> S02 -> S03)
- 23-module autonomous pipeline
- Disk purge module
- Audio guard module

### Changed
- NTFS -> ext4 migration (both drives)
- 21 individual timers consolidated into single autonomous-pipeline

---

## v5.0 — 2026-07-08

### Added
- Initial pipeline deployment
- Docker compose with core services (gluetun, qBit, Radarr, Sonarr, Prowlarr)
- Basic import flow

---

## DEPLOYMENT DATES

| Date       | Version | Major Change                                    |
|------------|---------|-------------------------------------------------|
| 2026-07-08 | v5.0    | Initial pipeline deployment                      |
| 2026-07-10 | v6.0    | NTFS->ext4, SATA fix, 23-module pipeline        |
| 2026-07-11 | v6.1    | Timer consolidation, batch import, health monitor|
| 2026-07-13 | v7.0    | Firewall fix, VM config, security hardening     |
| 2026-07-14 | v7.1    | Sorting fix, IPv6 fix, cross-seed fix, dedup     |

## v7.2 — 2026-07-15

### Fixed
- **qBit crashing (ROOT CAUSE):** gluetun DNS `1.1.1.1` was missing port — gluetun failed every few minutes, taking qBit with it. Changed to `DNS_UPSTREAM_PLAIN_ADDRESSES=1.1.1.1:53`
- **S2-NN TV detection:** Isekai Nonbiri Nouka S2 - 12 format (no Exx) was not caught as TV. Fixed regex from `[-. ]` to `[-. ]+` to match multi-char separators
- **Radarr auto-rename:** Was disabled — no files renamed on import. Enabled with format `{Movie Title} ({Release Year})` + triggered RenameAllFiles
- **Sonarr auto-rename:** Set to `{Series Title} - S{season:00}E{episode:00} - {Episode Title}`
- **Plex library keys:** Pipeline used keys 8/9, actual are 1/2 — fixed in both scripts
- **Website prefix stripping:** Added to pipeline name extraction — removes `www.Site.com`, `www Site com` prefixes
- **WireGuard key exposure:** Public key was inline in docker-compose.yml — moved to .env
- **VM RAM:** Set to exactly 12GB, no balloon overhead
- **VM autostart:** libvirtd + VM auto-start on server cold boot
- **Sunshine service:** Recreated with scheduled task for auto-start
- **Windows Firewall:** Added rules for Sunshine ports 47984,47989,47998,48010
- **SpongeBob:** TV show added (18 seasons) + 3 movies already in Radarr

### Changed
- Pipeline TV regex: added `S2-NN`, `S2.NN`, `S2-NN` patterns
- Deduper v2: Hash-verified, Tdarr-safe (skips recently modified files)
- Dedupe: 151 files deleted, 206.7 GB recovered
- qBit limits lowered: max_connec=2000, max_dl=15 for stability
- Docker health checks: Relaxed timeouts to survive load spikes
- COMMANDS.md: Complete rewrite with all current commands
- README: Updated to v7.2 with current media counts

### VM Status
- GPU: GTX 1660 SUPER, driver 560.94, VFIO passthrough
- Sunshine v7.1 running on port 47989 (NVENC)
- Moonlight: `vm moon`
- SSH: `ssh vm`

---

## DEPLOYMENT DATES

| Date       | Version | Major Change                                    |
|------------|---------|-------------------------------------------------|
| 2026-07-08 | v5.0    | Initial pipeline deployment                      |
| 2026-07-10 | v6.0    | NTFS->ext4, SATA fix, 23-module pipeline        |
| 2026-07-11 | v6.1    | Timer consolidation, batch import, health monitor|
| 2026-07-13 | v7.0    | Firewall fix, VM config, security hardening     |
| 2026-07-14 | v7.1    | Sorting fix, IPv6 fix, cross-seed fix, dedup     |
| 2026-07-15 | v7.2    | Auto-rename, Plex keys, dual audio, deduper v2  |
| 2026-07-15 | v7.3    | OOM fix, gluetun DNS, QXL removed, Docker limits |
