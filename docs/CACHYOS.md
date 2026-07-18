# CachyOS Desktop

## Hardware & Software

| Component | Detail |
|-----------|--------|
| **GPU** | NVIDIA RTX 3080 |
| **Driver** | nvidia-dkms 610.43.03 |
| **Display** | 1920×1080 @ 240 Hz, Wayland |
| **DE/WM** | KDE Plasma 6.7.2 / KWin 6.7.2 |
| **Moonlight** | v6.1.0 (flatpak) |
| **Audio** | PipeWire + Corsair HS55 Wireless USB |
| **Kernel** | linux-cachyos |

---

## Wayland Stability

### Crash History

**Date**: 2026-07-13  
**Symptom**: KWin SIGSEGV crashes (3 occurrences)  
**Root cause**: `GBM_BACKEND=nvidia-drm` in `/etc/environment` + missing cursor theme  

| # | Time | Trigger |
|---|------|---------|
| 1 | ~14:30 | Idle / screen lock |
| 2 | ~16:45 | Window focus change |
| 3 | ~18:10 | Application launch |

### Fixes Applied

```bash
# /etc/environment — REMOVED the following line:
# GBM_BACKEND=nvidia-drm

# Install cursor theme
sudo pacman -S breeze-cursors
```

### DRM Device Fix

```bash
# /etc/environment
KWIN_DRM_DEVICES=/dev/dri/card1
```

`card1` is the RTX 3080's render node. `card0` would select the wrong device.

### Plasma Watchdog

| Setting | Value |
|---------|-------|
| Config file | `~/.config/plasma-watchdogrc` |
| Interval | 30s |
| Action on crash | Restart plasmashell + kwin_x11/kwin_wayland |
| Restart limit | 5 attempts before full session restart |

```ini
# ~/.config/plasma-watchdogrc
[Watchdog]
Interval=30
MaxRestarts=5
Action=restart
```

### Recovery Commands

```bash
# Restart KWin
kwin_wayland --replace &

# Restart Plasma
plasmashell --replace &

# Full session restart
loginctl terminate-session $XDG_SESSION_ID

# Verify DRM device
ls -la /dev/dri/by-path/ | grep nvidia

# Check KWin crash logs
coredumpctl list kwin_wayland
coredumpctl info kwin_wayland
```

---

## VM Commands

Script location: `/usr/local/bin/` and `~/scripts/`

| Alias | Command | Purpose |
|-------|---------|---------|
| `moon` | `moonlight stream 10.0.0.128` | Stream Win10 desktop |
| `game` | `moonlight stream 10.0.0.128 --app SteamBigPicture` | Launch Steam Big Picture |
| `status` | `ssh server 'virsh list --all'` | Check VM state |
| `start` | `ssh server 'virsh start win10'` | Power on VM |
| `sec` | `ssh server 'virsh shutdown win10'` | Graceful shutdown |
| `health` | `ssh server 'systemctl is-active win10'` | Check VM service |
| `scanall` | `ssh server 'docker exec sonarr ... && docker exec radarr ... && docker exec lidarr ...'` | Trigger all library scans |
| `win` | `ssh -p 2225 10.0.0.128` | SSH into Windows VM |
| `sun` | `ssh 10.0.0.200` | SSH into server |
| `pair` | `moonlight pair 10.0.0.128` | Pair Moonlight with Sunshine |

---

## SSH Configuration

`~/.ssh/config`:

```
Host server
    HostName 10.0.0.200
    Port 2223
    User topaz
    IdentityFile ~/.ssh/id_ed25519

Host laptop
    HostName 10.0.0.234
    User topaz
    IdentityFile ~/.ssh/id_ed25519

Host win10
    HostName 10.0.0.128
    Port 2225
    User topaz
    IdentityFile ~/.ssh/id_ed25519

Host desktop
    HostName 10.0.0.192
    User topaz
    IdentityFile ~/.ssh/id_ed25519
```

---

## Moonlight Settings

### Stream Parameters

| Parameter | Value |
|-----------|-------|
| Resolution | 1920×1080 |
| FPS | 120 |
| Bitrate | 150 Mbps |
| Codec | HEVC (H.265) |
| VSync | Disabled (`--no-vsync`) |
| Frame pacing | Enabled (`--frame-pacing`) |
| Game optimization | Enabled (`--game-optimization`) |
| Absolute mouse | Disabled (`--no-absolute-mouse`) |
| Surrogate | Disabled |
| Quit app after | Enabled (`--quit-after`) |
| Fullscreen key combo | `Alt+Enter` |

### Hardware Decoding

| Priority | Backend | Capability |
|----------|---------|-------------|
| 1 (primary) | **Vulkan** | RTX 3080 native decode |
| 2 (fallback) | **VAAPI** | Software / iGPU |

### Session Stats (average)

| Metric | Value |
|--------|-------|
| Decode latency | 1.0 ms |
| Render latency | 2.14 ms |
| Network latency | 1.0 ms |
| Total latency | ~4.14 ms |
| Frames dropped | 0% |
| Host processing | < 3 ms |

### Full Client Command

```bash
moonlight stream \
  --resolution 1920x1080 \
  --fps 120 \
  --bitrate 150000 \
  --codec hevc \
  --no-vsync \
  --frame-pacing \
  --game-optimization \
  --no-absolute-mouse \
  --quit-after \
  10.0.0.128
```

---

## Audio

| Component | Detail |
|-----------|--------|
| Server | PipeWire |
| Device | Corsair HS55 Wireless (USB) |
| Profile | High Fidelity Playback (A2DP Sink, LDAC) |
| Sample rate | 48000 Hz |
| Channels | Stereo |

### Restart Commands

```bash
# PipeWire
systemctl --user restart pipewire pipewire-pulse wireplumber

# Audio sink device
pactl set-default-sink alsa_output.usb-Corsair_HS55-00.analog-stereo
```

---

## Autostart

| Entry | Path | Purpose |
|-------|------|---------|
| Watchdog | `~/.config/autostart/plasma-watchdog.desktop` | KWin/Plasma crash recovery |
| Jarvis | `~/.config/autostart/jarvis.desktop` | Custom assistant |
| EasyEffects | `~/.config/autostart/easyeffects.desktop` | Audio DSP / EQ |

---

## Performance Tuning

### KWin Settings

`~/.config/kwinrc`:

```ini
[Compositing]
LatencyPolicy=ExtremelyLow
OpenGLIsUnsafe=false
AllowFullScreenHack=true

[Blur]
Enabled=false

[RoundedCorners]
Enabled=false

[Windows]
GLFinish=false
```

| Setting | Value | Rationale |
|---------|-------|-----------|
| `LatencyPolicy` | `ExtremelyLow` | Minimize compositor input lag |
| `Blur` | Disabled | Reduce GPU overhead |
| `RoundedCorners` | Disabled | Reduce GPU overhead |
| `AllowFullScreenHack` | `true` | Unredirect fullscreen windows (bypass compositor) |

### NVIDIA Settings

```bash
# /etc/environment
KWIN_DRM_DEVICES=/dev/dri/card1

# Disable GSP firmware (stability)
# Kernel cmdline: nvidia.NVreg_EnableGpuFirmware=0
```

---

## GTA V Enhanced — YimMenu V2 Lua Scripts

**Installation:** `/home/topaz/Games/rockstar-games-launcher/drive_c/users/steamuser/AppData/Roaming/YimMenuV2/scripts/`
**Steam prefix:** Synced via `~/bin/yim-sync.sh`

### Custom Scripts (8)

| Script | Type | Function |
|--------|------|----------|
| zzz-money | One-shot | Fills nightclub/agency/arcade safes ($600K) |
| zzz-godmode | Loop | Godmode + Never Wanted (reload to stop) |
| zzz-teleport | One-shot | Set waypoint → reload → teleported |
| zzz-vehicle | One-shot | Fix + max upgrades current vehicle |
| zzz-weapons | One-shot | All MK2 weapons + 9999 ammo |
| zzz-heal | One-shot | Full health + armor + clear wanted |
| zzz-recovery | One-shot | Max stats, unlock all guns/tuning/clothes |
| zzz-properties | One-shot | Own all properties + upgrades |

### Original Scripts (10)
all-awards, all-collectibles, all-tattoos, biz-teroids, bunker-research, casino-reset, cluckinbell-skip, dre-skip, fast-respawn, jenette-skip

### YimMenu V2 Enhanced Lua API
**Available:** script.run_in_callback, script.yield(), natives.load_natives(), stats.*, notify.*, log.*, MONEY.*, NETWORK.*, ENTITY.*, PLAYER.*, PED.*, OBJECT.*, VEHICLE.*, STREAMING.*, HUD.*, PAD.*, TASK.*, CUTSCENE.*, WEAPON.*, transactions.*

**Not available:** gui, joaat, script.register_looped, script.run_in_fiber, script.register_callback, commands

**Money limitation:** FSL local saves block all Lua money transactions. Use YimMenu UI → Recovery → Transactions for direct wallet cash. Safe filler method works via stats API (collect at Nightclub/Agency/Arcade in-game). All hashes hardcoded (no joaat support).
