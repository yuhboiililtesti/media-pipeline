# ISSUES & SOLUTIONS — Complete Reference
# Updated: 2026-07-18 — Pipeline v7.4

---

## CRITICAL ISSUES (System Down / Data Loss Risk)

### #0: Gluetun DNS/Health Check Restart Loop — qBit Kept Going Offline
**Date:** 2026-07-18
**Symptom:** Gluetun container restarting 12x every ~5 minutes. qBit losing network attachment, download speeds dropping to 0, WebUI unreachable.
**Root Cause:** Gluetun's health check used `127.0.0.1:53` for DNS resolution (cloudflare.com/github.com). WireGuard tunnel blocks plain DNS on localhost. `DNS_UPSTREAM_PLAIN_ADDRESSES=1.1.1.1:53` didn't help because WireGuard overrides system DNS. Docker health check with `retries:10 x interval:30s = 300s` killed container every 5 minutes.
**Fix:** Set `DNS_KEEP_NAMESERVER=on` + `VPN_HEALTHCHECK_ENABLED=off`. Removed Docker health check block from compose. Full `docker compose down/up` to clear cached health state.
**Result:** 0 restarts, gluetun healthy, qBit stable at 97.5 MB/s DL indefinitely.

### #0b: Misplaced Media — TV Shows in Movies Directory
**Date:** 2026-07-18
**Symptom:** Mob Psycho 100 S1+S2, Attack on Titan S3, Family Guy S04 found in `/mnt/20TB/Movies 1/` instead of TV Shows.
**Root Cause:** Radarr misclassified anime/TV series as movies on import. Pipeline batch_import.py only sorts new downloads, doesn't scan existing files.
**Fix:** Manually moved misplaced content. Created `/opt/classify_media.py` with strong TV detection (S##E##, S##., Season #, EP##) and movie extra filtering. Installed `classify-media.timer` (every 6h). Auto-triggers Radarr/Sonarr rescan.
**Result:** All misplaced content corrected. Future misplacements caught automatically within 6 hours.

### #1: nftables/UFW Firewall Conflict — ROOT CAUSE of ALL LAN Access Issues
**Date:** 2026-07-13
**Symptom:** UFW rules not working. Plex, qBit, Sonarr, Radarr all unreachable from LAN.
**Root Cause:** nftables was the actual packet filter with `policy drop`. UFW wrote rules to iptables which were ignored. Only ports 22 and 2223 were allowed in nftables, blocking all other services.
**Fix:** Added 16+ missing port rules directly to `nftables INPUT` chain. Created `fix-nftables.service` that flushes and rebuilds clean rules on boot. Masked `nftables.service` (can't load xtables compat rules). Cleaned duplicate rules (chain had 5x copies of each rule).
**Result:** All services accessible from LAN. 26 TCP + 3 UDP ports open.

### #2: Plex EHOSTUNREACH
**Date:** 2026-07-13
**Symptom:** Plex unreachable from desktop/laptop.
**Root Cause:** Same as #1 — nftables blocking port 32400.
**Fix:** Port 32400 added to nftables INPUT chain.
**Result:** Plex accessible.

### #3: qBit WebUI Unreachable
**Date:** 2026-07-13
**Symptom:** qBit WebUI at port 8083 unreachable from LAN.
**Root Cause:** Same as #1 — nftables blocking port 8083.
**Fix:** Port 8083 added to nftables INPUT chain.
**Result:** qBit WebUI accessible.

### #4: Gaming VM Cold Boot Failure
**Date:** 2026-07-13
**Symptom:** VM wouldn't start after server reboot.
**Root Cause:** libvirtd was masked, gaming-vm.service not enabled.
**Fix:** Unmasked and enabled libvirtd, enabled gaming-vm.service, VM autostart configured. Cold boot chain: libvirtd enabled -> gaming-vm.service enabled -> VM autostart enabled -> VFIO in initramfs.
**Result:** VM starts automatically on boot.

### #5: Pipeline Sorting — Movies Misclassified as TV
**Date:** 2026-07-14
**Symptom:** Some movies ended up in TV Shows directories. Pipeline moved movies to wrong location.
**Root Cause:** Simple regex `[Ss]\d{2}[Ee]\d{2}` in section 7 was too narrow, and some movie filenames accidentally matched TV patterns.
**Fix:** Rewrote auto-import (section 7) in autonomous-pipeline.py v7.1 with:
- Strong TV signals: SxxExx, Sxx., Season X
- False positive exclusions: "complete series", "collection", "anthology"
- Show name extraction with clean release tag removal
- Cross-type dedup against both movie and TV directories
**Result:** Correct classification, no cross-contamination.

### #6: Batch Import Moving Movies to TV Shows
**Date:** 2026-07-14
**Symptom:** batch_import.py misclassifying movies as TV episodes.
**Root Cause:** `is_tv()` regex matched "COMPLETE" keyword, weak detection.
**Fix:** Rewrote batch_import.py v3 with strong TV signal detection, movie false-positive exclusions, cross-type dedup, size-based dedup.
**Result:** Correct sorting, dedup working.

---

## HIGH PRIORITY ISSUES (Service Degraded)

### #7: qBit Unreachable by Pipeline (IPv6)
**Date:** 2026-07-14
**Symptom:** Pipeline couldn't connect to qBit at localhost:8083. Error: "Cannot get torrents!"
**Root Cause:** Docker's qBit listens on IPv4 only, but `localhost` resolves to `::1` (IPv6) first.
**Fix:** Changed config.json `qbit.server` from `http://localhost:8083` to `http://127.0.0.1:8083`.
**Result:** Pipeline connects successfully.

### #8: cross-seed Crash-Loop
**Date:** 2026-07-14
**Symptom:** cross-seed container restarting every few seconds.
**Root Cause:** Hardlinks can't cross drives (/mnt/8TB -> /mnt/20TB). Error: "EPERM: operation not permitted".
**Fix:** Changed `linkType` from `hardlink` to `symlink` in cross-seed config.js.
**Result:** cross-seed starts and runs normally.

### #9: All Torrents Entered Error State
**Date:** 2026-07-10
**Symptom:** Every torrent errored with "skipping tracker announce (unreachable)".
**Root Cause:** Dead trackers (RARBG shutdown), SATA failure, DHT couldn't find peers.
**Fix:** Deleted all errored torrents, triggered fresh searches, let RSS repopulate.
**Result:** Pipeline recovered to 195+ torrents.

### #10: Laptop qBit Overloaded (1,303 torrents)
**Date:** 2026-07-10
**Symptom:** ThinkPad SL510 with 1,303 dead/stalled torrents.
**Fix:** Deleted all but active downloads, set limits: 10 active DL, 25 max, 15MB/s.
**Result:** Stable.

### #11: Quality Profiles Not Upgrading
**Date:** 2026-07-13
**Symptom:** Sonarr/Radarr not upgrading existing downloads to better quality.
**Fix:** Set upgradeAllowed=True on Sonarr profile ID:3 (cutoff Bluray-1080p) and Radarr profile ID:6.
**Result:** Upgrades enabled.

### #12: Dead/Stalled Torrents Accumulating
**Date:** 2026-07-13
**Symptom:** 27 paused dead + 9 stalled + 4 errored torrents cluttering qBit.
**Fix:** Manual cleanup + anti-seed.py v2 only cleans dead/zero-seed.
**Result:** Clean torrent list.

---

## MEDIUM PRIORITY ISSUES (Security / Configuration)

### #13: FlareSolverr Exposed to Network
**Date:** 2026-07-13
**Symptom:** FlareSolverr bound to 0.0.0.0, accessible from LAN.
**Fix:** Bound to 127.0.0.1:8191.
**Result:** Only accessible from localhost.

### #14: SSH Password Authentication Enabled
**Date:** 2026-07-13
**Symptom:** Server accepting password login (security risk).
**Fix:** Generated ed25519 keypair, deployed to server, disabled password auth.
**Result:** Key-based auth only.

### #15: WireGuard Keys in docker-compose.yml
**Date:** 2026-07-13
**Symptom:** VPN keys hardcoded in docker-compose.yml (security risk).
**Fix:** Moved to /mnt/20TB/homelab/media/compose/.env with perms 600.
**Result:** Secrets not in version-controlled file.

### #16: Memory Limits Missing on Containers
**Date:** 2026-07-13
**Symptom:** Several containers had no memory limits.
**Fix:** Added mem_limit: tdarr-node (2GB), qbittorrent (4GB), immich-redis (512MB), immich-postgres (1GB), decluttarr (256MB).
**Result:** All containers have memory limits.

### #17: Non-English Content Leaking Through
**Date:** 2026-07-10
**Symptom:** French, Italian, Spanish content in qBit.
**Fix:** NON_ENG keyword filter in pipeline — auto-deletes non-English torrents.
**Result:** Only English + anime dual-audio content stays.

### #18: 4K/2160p Content Being Downloaded
**Date:** 2026-07-10
**Symptom:** Quality profiles allowed 4K.
**Fix:** Nuked 2160p from all quality profiles. TV -> 720p, Movies -> 1080p.
**Result:** NO 4K, NO cam rips permitted.

---

## LOW PRIORITY ISSUES (Annoyances / Cleanup)

### #19: NIC Power Saving Causing Packet Loss
**Date:** 2026-07-13
**Symptom:** Occasional network drops, TCP connections timing out.
**Fix:** Disabled NIC power saving, set TCP keepalive 60s/10s/6 probes, enabled Wake-on-LAN.
**Result:** Stable network.

### #20: Failed Systemd Services
**Date:** 2026-07-13
**Symptom:** transmission-daemon, fwupd, fwupd-refresh failing.
**Fix:** Disabled transmission-daemon, masked fwupd and fwupd-refresh.
**Result:** Zero failed services.

### #21: No Cross-Drive Dedup
**Date:** 2026-07-14
**Symptom:** Same file existing on both 20TB and 8TB, wasting space.
**Fix:** media-dedupe.py scans all 4 media dirs, picks keeper based on TV Shows priority + organized subdirectory scoring. First run: 79 dupes deleted, 132.8 GB recovered.
**Result:** Dedup working.

### #22: Files Not Being Renamed After Import
**Date:** 2026-07-10
**Symptom:** Files sitting with raw torrent names.
**Fix:** Configured Radarr/Sonarr naming conventions.
**Result:** All files properly renamed on import.

### #23: Plex Not Auto-Scanning After Imports
**Date:** 2026-07-10
**Symptom:** Files imported but Plex didn't see them.
**Fix:** Added Plex notification in Radarr/Sonarr + pipeline triggers scan.
**Result:** Plex sees new content within seconds.

### #24: Docker Data-Root on Failing Drive
**Date:** 2026-07-10
**Symptom:** Docker couldn't start when 20TB had I/O errors.
**Fix:** Moved docker data to /mnt/8TB/docker-data. Added /etc/docker/daemon.json.
**Result:** Docker starts even if 20TB drive has issues.

---

## HISTORICAL ISSUES (v6.0 and Earlier)

### #25: SATA Cable Failure on 20TB Drive
**Date:** 2026-07-10
**Symptom:** I/O errors, kernel hangs, drive remounted read-only.
**Fix:** Physically reseated SATA cable.
**Result:** Drive stable.

### #26: Prowlarr Database Corruption
**Date:** 2026-07-08
**Symptom:** Prowlarr wouldn't start.
**Fix:** Nuked Prowlarr config, rebuilt from scratch.
**Result:** 13 indexers re-added.

### #27: Indexer Drought (7 indexers, zero content)
**Date:** 2026-07-10
**Symptom:** MissingEpisodeSearch returned 0 releases.
**Fix:** 13 Prowlarr indexers + FlareSolverr deployed.
**Result:** Good content discovery.

### #28: Seasonal Downloads Were Random
**Date:** 2026-07-10
**Symptom:** Episodes downloaded randomly across seasons.
**Fix:** Implemented Seasonal Cascade module.
**Result:** Shows download S01 -> S02 -> S03.

### #29: Multiple Pipelines Overlapping
**Date:** 2026-07-10
**Symptom:** 21 failed systemd services, all hitting at same time.
**Fix:** Consolidated into single autonomous-pipeline with 23 modules.
**Result:** No timer overlaps.

### #30: CachyOS Desktop Samba Mounts Broken
**Date:** 2026-07-10
**Symptom:** Old fstab had wrong share names.
**Fix:** Updated fstab with correct share names.
**Result:** All 4 server drives mounted.

### #31: Duplicate Queue Entries in Sonarr
**Date:** 2026-07-08
**Symptom:** 20 duplicate entries stuck in warning state.
**Fix:** Deleted orphaned queue entries via API.
**Result:** Queue clean.

### #32: Orphaned "Missing root folder" Warnings
**Date:** 2026-07-08
**Symptom:** Multiple root folders missing warnings.
**Fix:** Removed old root folder paths via API.
**Result:** Warnings cleared.

### #33: Sonarr Missing ffprobe
**Date:** 2026-07-08
**Symptom:** Sonarr couldn't detect media files.
**Fix:** docker exec sonarr apk add --no-cache ffmpeg.
**Result:** Media detection working.

### #34: VM Disk Resize (550GB -> 1TB)
**Date:** 2026-07-14
**Symptom:** VM disk too small for game installs.
**Fix:** Shutdown VM, resized QCOW2 to 1TB, expanded NTFS partition.
**Note:** NTFS has cluster inconsistencies — needs chkdsk /f on first Windows boot.
**Result:** 1TB virtual disk.
