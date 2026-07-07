# Pipeline-Doc — HARDWARE

## Server (plexy) — <server-ip>
```
CPU:    Multi-core x86_64
GPU:    NVIDIA GeForce RTX 3090 Ti (10de:2203, 24GB VRAM, NVENC)
OS:     Arch Linux (LVM: root 86.8G ext4, home 24G ext4)
NIC:    enp6s0f0
SSH:    <user>@<server-ip> -p 2223 (~/.ssh/id_ed25519)

DISK INVENTORY:
┌─────────┬─────────┬─────────────┬───────┬──────────────────────────┐
│ Device  │ Size    │ Mount       │ FS    │ Model                    │
├─────────┼─────────┼─────────────┼───────┼──────────────────────────┤
│ sda2    │ 18.2 TB │ /mnt/20TB   │ NTFS  │ ST20000NM007D-3DJ103     │
│ sdc2    │  7.3 TB │ /mnt/8TB    │ NTFS  │ ST8000DM004-2U9188       │
│ sdb LVM │111.8 GB │ /, /home    │ ext4  │ WDC WDS120G2G0A-00JH30   │
│ nvme0n1 │  1.8 TB │ UNMOUNTED   │ ext4  │ Samsung 970 EVO Plus      │
│         │         │ RETIRED     │       │ FAILURE: reset error -19 │
└─────────┴─────────┴─────────────┴───────┴──────────────────────────┘

zram: 4GB swap
```

## Laptop — <laptop-ip>
```
CPU:    Dual-core
RAM:    3.7 GB
OS:     Ubuntu 24.04 (btrfs: root 25G, /home 202G)
Disk:   232.9 GB HDD (WDC WD2500BEVT-0)
NIC:    enp8s0 (ethernet ONLY, static <laptop-ip>/24)
        Gateway: <router-ip>, DNS: 1.1.1.1, 8.8.8.8
WiFi:   wlp5s0 — DISABLED + MASKED
SSH:    laptop@<laptop-ip> -p 2225 (~/.ssh/opencode_remote)
```

## Desktop — <desktop-ip>
```
OS:     CachyOS (Arch-based)
Role:   Admin workstation + backup target
Kernel: linux-cachyos-lts (BO3 compat)
Disk:   500gb-1 (465GB, 94GB free — homelab backup)
        500gb-2 (465GB, 70GB free — SteamLibrary)
```

## Drive Health Monitoring
```
disk-watchdog.timer: every 30 min — SMART monitoring
disk-space-guard.timer: every 15 min — space alerts

Thresholds:
  Warning: >85%
  Critical: >95%
  Emergency: >98%
```
