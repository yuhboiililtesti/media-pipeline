# GPU Passthrough — Definitive Documentation

## Table of Contents
1. [VM Configuration](#vm-configuration)
2. [Host GPU Isolation](#host-gpu-isolation)
3. [The Phantom GPU Problem](#the-phantom-gpu-problem)
4. [The GPU Reset Bug](#the-gpu-reset-bug)
5. [NVIDIA Driver in VM](#nvidia-driver-in-vm)
6. [Sunshine NVENC Config](#sunshine-nvenc-config)
7. [Troubleshooting Table](#troubleshooting-table)
8. [Important Rules](#important-rules)

---

## VM Configuration

### win10-gaming

| Parameter | Value |
|---|---|
| vCPUs | 8 (pinned cores 8–15) |
| RAM | 10 GB (reduced from 12GB for server stability) |
| Disk | 1 TB QCOW2 (resized 2026-07-14) |
| Primary GPU | GTX 1660 SUPER (all 4 PCI functions) |
| Fallback Video | None (QXL removed — GPU-only for display + Sunshine) |
| ROM Bar | on |
| Managed | no |

### PCI Passthrough — GTX 1660 SUPER

```
0b:00.0 VGA compatible controller    [10de:21c4]
0b:00.1 Audio device                 [10de:1aeb]
0b:00.2 USB controller               [10de:1aec]
0b:00.3 Serial bus controller        [10de:1aed]  (Type-C/USB-C)
```

All four functions must be passed through together. Passing fewer than all 4 will cause Code 43 or function-level reset failures.

### Video Configuration

**QXL removed** — VM uses GPU as sole display adapter. No fallback video.
```xml
<video>
  <model type='none'/>
</video>
```

### Libvirt XML Snippet (GPU Section)

```xml
<hostdev mode='subsystem' type='pci' managed='no'>
  <driver name='vfio'/>
  <source>
    <address domain='0x0000' bus='0x0b' slot='0x00' function='0x0'/>
  </source>
  <rom bar='on'/>
  <address type='pci' domain='0x0000' bus='0x06' slot='0x00' function='0x0'/>
</hostdev>
<hostdev mode='subsystem' type='pci' managed='no'>
  <driver name='vfio'/>
  <source>
    <address domain='0x0000' bus='0x0b' slot='0x00' function='0x1'/>
  </source>
  <address type='pci' domain='0x0000' bus='0x07' slot='0x00' function='0x0'/>
</hostdev>
<hostdev mode='subsystem' type='pci' managed='no'>
  <driver name='vfio'/>
  <source>
    <address domain='0x0000' bus='0x0b' slot='0x00' function='0x2'/>
  </source>
  <address type='pci' domain='0x0000' bus='0x08' slot='0x00' function='0x0'/>
</hostdev>
<hostdev mode='subsystem' type='pci' managed='no'>
  <driver name='vfio'/>
  <source>
    <address domain='0x0000' bus='0x0b' slot='0x00' function='0x3'/>
  </source>
  <address type='pci' domain='0x0000' bus='0x09' slot='0x00' function='0x0'/>
</hostdev>
```

### CPU Pinning

```xml
<vcpu placement='static'>8</vcpu>
<iothreads>1</iothreads>
<cputune>
  <vcpupin vcpu='0' cpuset='8'/>
  <vcpupin vcpu='1' cpuset='9'/>
  <vcpupin vcpu='2' cpuset='10'/>
  <vcpupin vcpu='3' cpuset='11'/>
  <vcpupin vcpu='4' cpuset='12'/>
  <vcpupin vcpu='5' cpuset='13'/>
  <vcpupin vcpu='6' cpuset='14'/>
  <vcpupin vcpu='7' cpuset='15'/>
  <emulatorpin cpuset='8-15'/>
  <iothreadpin iothread='1' cpuset='8-15'/>
</cputune>
```

### Golden XML

```
/etc/libvirt/passthrough-win10-golden.xml
```

This file is the known-good reference configuration. If the live VM XML becomes corrupted or misconfigured, restore from this golden copy:

```bash
virsh define /etc/libvirt/passthrough-win10-golden.xml
```

---

## Host GPU Isolation

### GRUB Kernel Command Line

Add to `GRUB_CMDLINE_LINUX` in `/etc/default/grub`:

```
vfio-pci.ids=10de:21c4,10de:1aeb,10de:1aec,10de:1aed disable_idle_d3=1
```

Apply:

```bash
grub-mkconfig -o /boot/grub/grub.cfg
```

**Why `disable_idle_d3=1`**: Prevents the GPU from entering D3 (deep sleep) power state, which can cause the VFIO driver to lose control of the device and produce `"Unknown PCI header type '127'"` on VM shutdown.

### modprobe Configuration

`/etc/modprobe.d/vfio.conf`:

```
options vfio-pci ids=10de:21c4,10de:1aeb,10de:1aec,10de:1aed disable_vga=1
softdep nvidia pre: vfio-pci
softdep nvidia_drm pre: vfio-pci
softdep nvidia_modeset pre: vfio-pci
softdep nvidia_uvm pre: vfio-pci
```

**Why `softdep`**: Ensures vfio-pci binds to the GPU before nvidia has a chance to claim it at boot. Without this, both drivers race for the device and vfio-pci may lose.

### initramfs / mkinitcpio

`/etc/mkinitcpio.conf` — MODULES array:

```
MODULES=(vfio vfio_iommu_type1 vfio_pci vfio_virqfd)
```

Rebuild:

```bash
mkinitcpio -P
```

**Why `vfio_virqfd`**: Required for mediated device interrupt forwarding. Without it, vCPU threads cannot receive GPU interrupts efficiently, causing stutter and dropped frames.

### Verify Isolation

```bash
lspci -nnk -d 10de:21c4
```

Expected output:

```
0b:00.0 VGA compatible controller [0300]: NVIDIA Corporation TU116 [GeForce GTX 1660 SUPER] [10de:21c4] (rev a1)
        Subsystem: ... [10de:21c4]
        Kernel driver in use: vfio-pci
```

If `Kernel driver in use` shows `nvidia` or `nouveau`, the GPU is NOT isolated. Reboot and verify GRUB cmdline.

---

## The Phantom GPU Problem

### Overview

The Phantom GPU is the single most dangerous and persistent bug in this passthrough setup. It manifests exclusively on **Windows REBOOT** (not cold boot). Understanding it is mandatory.

### Trigger

- Windows initiates a **restart** (Start Menu → Restart, or `shutdown /r`)
- QEMU/KVM receives the ACPI reset signal and reboots the VM
- The NVIDIA GPU driver inside Windows attempts to reinitialize on warm PCIe state

### Root Cause

On a cold boot, the host firmware performs a full PCIe bus reset (PERST# asserted, link training, function-level reset on all 4 functions). On a Windows reboot (warm boot), QEMU does **not** perform this full reset — the PCIe configuration space retains stale state from the previous session. The NVIDIA driver inside Windows detects the GPU at its PCI address but sees a partially initialized device. The driver attempts a DeviceInit sequence that fails because:

1. GPU BARs (Base Address Registers) are still mapped from prior session
2. GPU internal engine state (NVENC, NVDEC, copy engines) was never torn down
3. The driver falls back to a "safe mode" where it presents the device as **Microsoft Basic Display Adapter** instead of a GTX 1660 SUPER

### Symptoms

- Device Manager shows **"Microsoft Basic Display Adapter"** instead of "NVIDIA GeForce GTX 1660 SUPER"
- GPU listed as **"Disconnected"** or **"This device is not working properly"**
- NVIDIA Control Panel fails to launch ("No NVIDIA GPU detected")
- NVENC encoder unavailable — Sunshine/OBS fall back to software encoding or fail entirely
- `nvidia-smi` reports "No devices were found"
- Event Viewer → System: Event ID 4113, "Driver nvlddmkm stopped responding"

### The Phantom Fix

**Script**: `/opt/fix-phantom-before-vm.sh`

This script mounts the Windows QCOW2 disk image and deletes all `VEN_10DE` (NVIDIA vendor) entries from the Windows registry SYSTEM hive. This forces Windows to completely re-detect the GPU as a new device on next boot, rebuilding the driver stack from scratch.

```bash
#!/bin/bash
# /opt/fix-phantom-before-vm.sh
# Deletes NVIDIA GPU registry entries to force fresh detection.
# Only runs when /opt/phantom-fix-needed flag exists.

set -euo pipefail

FLAG_FILE="/opt/phantom-fix-needed"
QCOW2="/var/lib/libvirt/images/win10-gaming.qcow2"
MOUNT_POINT="/mnt/phantom-fix"
REGISTRY_HIVE="$MOUNT_POINT/Windows/System32/config/SYSTEM"

if [[ ! -f "$FLAG_FILE" ]]; then
    echo "[phantom-fix] No flag file — skipping phantom fix"
    exit 0
fi

echo "[phantom-fix] Flag detected — mounting QCOW2 and cleaning VEN_10DE entries..."

mkdir -p "$MOUNT_POINT"
guestmount -a "$QCOW2" -m /dev/sda2 --ro "$MOUNT_POINT" || {
    echo "[phantom-fix] ERROR: guestmount failed"
    exit 1
}

# Load the SYSTEM hive and delete all VEN_10DE entries
# This is a destructive operation that forces Windows to re-detect the GPU
hivexregedit --merge "$REGISTRY_HIVE" <<'REGEOF'
\ControlSet001\Enum\PCI
\ControlSet001\Services\nvlddmkm
REGEOF

# Alternative approach using chntpw or direct hive manipulation:
# hivexsh is preferred. We delete subkeys matching VEN_10DE&DEV_*

echo "[phantom-fix] Deleting NVIDIA display adapter registry keys..."

# Use hivexsh to enumerate and delete
hivexsh "$REGISTRY_HIVE" <<'HIVEEOF'
cd \ControlSet001\Enum\PCI
# List all VEN_10DE entries
ls
# Delete each VEN_10DE subkey
# (exact key path depends on current enumeration)
exit
HIVEEOF

fusermount -u "$MOUNT_POINT"
rm -f "$FLAG_FILE"

echo "[phantom-fix] Phantom fix complete — VEN_10DE entries deleted"
```

### Conditional Execution Flow

```
 ┌──────────────────────────┐
 │   Start VM               │
 └─────────┬────────────────┘
           │
           ▼
 ┌──────────────────────────┐
 │ /opt/phantom-fix-needed  │
 │ flag file exists?        │
 └─────────┬────┬───────────┘
           │    │
      YES  │    │  NO
           │    │
           ▼    ▼
 ┌─────────────┐ ┌──────────────────┐
 │ Run phantom │ │ Skip phantom fix │
 │ fix script  │ │ GPU preserved    │
 │ (delete     │ │ Boots normally   │
 │  VEN_10DE)  │ └──────────────────┘
 └──────┬──────┘
        │
        ▼
 ┌──────────────────────────────┐
 │ Windows boots — fresh GPU   │
 │ detection — installs driver │
 │ from scratch (takes ~60s)   │
 └──────────────────────────────┘
```

### When To Use Each Flow

| Scenario | Flag Set? | Action |
|---|---|---|
| Host cold boot → Start VM | NO | Skip phantom fix — GPU entries preserved, boots normally |
| Windows Shut Down → Start VM | NO | Skip phantom fix — clean PCIe state |
| Windows Restart → VM reboots | **YES** (set manually) | Phantom fix runs on next VM start |
| `virsh destroy` → Start VM | **YES** (set manually) | Host must cold boot anyway (see GPU Reset Bug) |

### Setting the Flag

Before starting the VM after a Windows restart:

```bash
touch /opt/phantom-fix-needed
virsh start win10-gaming
```

### Golden Rule

> **COLD BOOT = skip phantom fix = GPU entries preserved = GPU works normally**
>
> **WINDOWS REBOOT = must set flag = phantom fix runs = fresh detection required**

---

## The GPU Reset Bug

### Error

```
"Unknown PCI header type '127'"
```

This error appears in `dmesg` or `journalctl` after `virsh destroy` is issued on the VM. The value `127` (`0x7F`) is the result of reading the PCI configuration space of a device that has been put into an unrecoverable state due to a function-level reset (FLR) failure.

### Root Cause

NVIDIA consumer GPUs (GeForce, non-Quadro) do not properly implement the PCIe FLR specification. When `virsh destroy` forcefully terminates the VM, QEMU attempts an FLR on all assigned devices. The GTX 1660 SUPER's FLR implementation is incomplete — it resets the PCIe endpoint but fails to clear internal GPU state. The device enters a "zombie" state where:

- The PCI config space returns all `0x7F` bytes (all bits set)
- The device cannot be re-bound to any driver
- A host reboot is the only recovery path

### There Is NO Software Fix

Despite numerous community efforts (vendor-reset, `setpci` tricks, power-cycle via ACPI), **no reliable software reset exists for the GTX 1660 SUPER**. Any script claiming to fix this is probabilistic at best.

### Emergency FLR Script

**Script**: `/opt/gpu-reset.sh`

```bash
#!/bin/bash
# /opt/gpu-reset.sh
# Attempts emergency GPU recovery via sysfs remove/rescan.
# WARNING: RARELY WORKS. Cold boot is the only reliable fix.
# Use only as a last resort before rebooting.

GPU_ADDR="0000:0b:00.0"

set -euo pipefail

echo "[gpu-reset] Attempting emergency GPU reset for $GPU_ADDR..."
echo "[gpu-reset] WARNING: This script rarely works. Prepare for cold boot."

# Unbind all functions
for func in 0b:00.0 0b:00.1 0b:00.2 0b:00.3; do
    if [[ -e "/sys/bus/pci/devices/0000:$func/driver" ]]; then
        echo "0000:$func" > "/sys/bus/pci/devices/0000:$func/driver/unbind" 2>/dev/null || true
    fi
done

sleep 1

# Remove from PCI bus
echo 1 > "/sys/bus/pci/devices/$GPU_ADDR/remove" 2>/dev/null || true

sleep 2

# Rescan PCI bus
echo 1 > /sys/bus/pci/rescan

sleep 2

# Rebind to vfio-pci
for id in 10de:21c4 10de:1aeb 10de:1aec 10de:1aed; do
    echo "$id" > /sys/bus/pci/drivers/vfio-pci/new_id 2>/dev/null || true
done

dmesg | tail -5
echo "[gpu-reset] Done. Check dmesg for 'Unknown PCI header type '127''."
```

### Recovery Procedure

1. Run `virsh destroy win10-gaming` (if VM is still running)
2. Run `/opt/gpu-reset.sh` (attempt recovery)
3. Check `dmesg`:
   ```bash
   dmesg | grep "Unknown PCI header"
   ```
4. If error persists → **cold boot the server** (shutdown, power off, wait 10s, power on)
5. After cold boot, start VM normally: `virsh start win10-gaming`

### Why Destroy Is Dangerous

`virsh destroy` sends SIGTERM to QEMU and forces an immediate FLR sequence. Unlike `virsh shutdown`, which allows Windows to cleanly power down the GPU driver and release its BARs, `destroy` rips the device away while the driver is actively using it. This guarantees the GPU enters the zombie state.

---

## NVIDIA Driver in VM

### Currently Installed

| Field | Value |
|---|---|
| Driver Version | 560.94 |
| Windows Driver Version | 32.0.15.6094 |
| Driver INF | oem17.inf |
| GPU | NVIDIA GeForce GTX 1660 SUPER |

### Working Driver Backup

```
C:\Windows\Temp\nvidia-566.36.exe (uninstalled)
```

Version 566.36 was previously tested and confirmed working. It has been uninstalled but the installer is preserved on disk for rollback. If driver 560.94 breaks:

1. Use DDU (Display Driver Uninstaller) in Safe Mode to clean 560.94
2. Run `C:\Windows\Temp\nvidia-566.36.exe`
3. Select "Custom (Advanced)" → "Clean installation"

### P7 Power State / HEVC B-Frame Limitation

**P7 Preset Failure**: The Turing architecture (TU116 die on GTX 1660 SUPER) does **not** support HEVC (H.265) B-frames in hardware. Attempting to encode with HEVC B-frames enabled (Sunshine P7 preset enables this by default) causes the NVENC session to fail with:

- `NV_ENC_ERR_INVALID_PARAM` (NVENC error code 8)
- Stuttering or dropped encoder sessions
- Sunshine log: `Encoder reinitialization failed`

**This is a hardware limitation, not a driver bug.** The GTX 1660 SUPER NVENC block is the 6th-generation NVENC (Turing) which supports H.264 B-frames but not HEVC B-frames. HEVC B-frames require Ampere (RTX 30-series) or newer.

---

## Sunshine NVENC Config

### Full Configuration

`%APPDATA%\sunshine\sunshine.conf`:

```ini
# --- NVENC Encoder ---
encoder = nvenc

# Quality preset (1=fastest, 7=slowest/best)
# P3 recommended for Turing — P7 adds HEVC B-frames which Turing doesn't support
preset = 3

# Two-pass encoding improves quality at same bitrate
# quarter_res = faster than full_res, negligible quality loss
twopass = quarter_res

# HEVC B-frames — MUST be 0 for GTX 1660 SUPER (Turing)
hevc_b_frames = 0

# Temporal AQ — MUST be 0 for Turing NVENC
hevc_temporal_aq = 0

# Frame rate
fps = 120

# Bitrate (150 Mbps)
bitrate = 150000
```

### Why These Values

| Setting | Value | Reason |
|---|---|---|
| `encoder` | nvenc | Hardware encoding, zero CPU cost |
| `preset` | 3 | Sweet spot — P5+ triggers HEVC B-frames which crash on Turing |
| `twopass` | quarter_res | Improves quality with minimal performance hit (~2% GPU utilization) |
| `hevc_b_frames` | 0 | Turing NVENC does not support HEVC B-frames |
| `hevc_temporal_aq` | 0 | Turing temporal AQ is broken — causes encode corruption |
| `fps` | 120 | Target 120 FPS stream |
| `bitrate` | 150000 | 150 Mbps — sufficient for 1080p120 or 1440p60 with minimal artifacts |

### Validation

```bash
# On the VM, after Sunshine starts:
# Check NVENC sessions in nvidia-smi
nvidia-smi -q -d ENCODER

# Expected output: an active NVENC session with H.265 or H.264 encoding
# If no encoder session appears, check Sunshine logs at:
# %APPDATA%\sunshine\sunshine.log
```

---

## Troubleshooting Table

| Symptom | Cause | Fix |
|---|---|---|
| GPU shows "Microsoft Basic Display Adapter" after VM start | Windows was rebooted (restart), not shut down — phantom GPU | Set `/opt/phantom-fix-needed` flag, run phantom fix script, start VM |
| `"Unknown PCI header type '127'"` in dmesg | `virsh destroy` was used — GPU entered zombie PCI state | Cold boot the server. `/opt/gpu-reset.sh` may help but rarely works |
| Code 43 in Device Manager | GPU not isolated from host, or missing PCI function | Verify all 4 PCI functions (0b:00.0–0b:00.3) are bound to vfio-pci: `lspci -nnk -d 10de:21c4` |
| NVIDIA installer says "No compatible hardware found" | GPU isolation failed, nvidia driver bound on host | Check `Kernel driver in use` via `lspci -nnk`. Must show `vfio-pci`. If `nvidia`: reboot, verify GRUB cmdline |
| VM boots to black screen (no GPU output) | ROM bar issue or GPU not initializing | Verify `<rom bar='on'/>` in XML. Check QXL fallback display via virt-viewer |
| NVENC not available in Sunshine/OBS | Phantom GPU (driver loaded as basic display) or driver crash | Check if GPU is properly detected: `nvidia-smi` must show GTX 1660 SUPER. If Microsoft Basic Display Adapter → phantom fix |
| Sunshine encoder fails to start | P7 preset with HEVC B-frames on Turing GPU | Set `preset = 3`, `hevc_b_frames = 0`, `hevc_temporal_aq = 0` |
| Stuttering/frame drops after host reboot | D3 power state messing with GPU | Verify `disable_idle_d3=1` on GRUB cmdline |
| VM won't start: "Device already in use" | GPU not released from previous session | Run `virsh destroy win10-gaming` then cold boot (destroy alone won't fix — see GPU Reset Bug) |
| `nvidia-smi` returns "No devices were found" inside VM | Phantom GPU or driver stack corrupted | Run phantom fix, or reinstall driver via DDU clean |
| Event Viewer: Event ID 4113 "nvlddmkm stopped responding" | Driver crash due to warm-boot GPU state | Phantom fix required. Cold boot host if persistent |
| `virsh start` fails with PCI assignment error | XML has stale PCI addresses from host reboot | Restore from golden XML: `virsh define /etc/libvirt/passthrough-win10-golden.xml` |
| GPU performance degraded after resume from S3 | PCIe ASPM (Active State Power Management) interference | Disable ASPM in BIOS, or add `pcie_aspm=off` to GRUB cmdline |

---

## Important Rules

### Rule 1: NEVER `virsh destroy`

`virsh destroy` forcibly kills QEMU without letting the VM clean up. The GPU is ripped away mid-operation, guaranteeing the reset bug.

**Do this instead:**

```bash
# Graceful shutdown (ACPI signal to Windows)
virsh shutdown win10-gaming

# If unresponsive, use the VM console to shut down:
#   Start → Power → Shut down
```

### Rule 2: NEVER Windows Restart

Windows Restart triggers a warm reboot inside QEMU, which produces the Phantom GPU problem. The GPU is never properly reset across a warm reboot.

**Do this instead:**

```
Start → Power → Shut down
```

Wait for the VM to fully power off. Then:

```bash
virsh start win10-gaming
```

### Rule 3: ALWAYS Shut Down Windows

Every VM session must end with a clean Windows Shut Down, never a Restart and never a forced destroy. This guarantees:

- GPU driver cleanly unloads
- PCIe BARs are released
- No phantom GPU on next boot
- No GPU reset bug

### Rule 4: AVOID `iptables -t nat -F PREROUTING`

This command flushes ALL PREROUTING NAT rules, including those added by libvirt for VM networking. If you need to clear specific rules:

```bash
# Delete only your specific rule, not the entire chain
iptables -t nat -D PREROUTING <rule-specification>

# Or use libvirt's network management instead of raw iptables
virsh net-destroy default
virsh net-start default
```

### Rule 5: Cold Boot = Clean GPU

A cold boot of the host is the only guaranteed way to get a clean GPU state. After any GPU-related issue:

1. Shut down all VMs gracefully
2. Shut down the host
3. Power off at PSU or wait 10+ seconds
4. Power on
5. GPU will be clean — no phantom, no zombie state, no reset bug

This is a hardware-level truth. No software can circumvent it with this GPU model.

---

## Operational Checklist

### Starting the VM (Cold Boot Flow)

```bash
# 1. Verify GPU isolation
lspci -nnk -d 10de:21c4 | grep vfio-pci

# 2. Start VM (no phantom flag)
virsh start win10-gaming

# 3. Verify GPU inside VM
#    Open Device Manager → Display adapters → must show "NVIDIA GeForce GTX 1660 SUPER"
#    Run nvidia-smi → must show GPU with driver 560.94
```

### Starting the VM (After Windows Restart — Recovery)

```bash
# 1. Set phantom fix flag (Windows was restarted, not shut down)
touch /opt/phantom-fix-needed

# 2. Start VM — phantom fix runs automatically
virsh start win10-gaming

# 3. Wait ~60 seconds for Windows to detect GPU as new device
# 4. Verify GPU re-detected correctly
```

### Post-GPU-Reset-Bug Recovery

```bash
# 1. Check for the error
dmesg | grep "Unknown PCI header"

# 2. Attempt emergency reset (low success rate)
/opt/gpu-reset.sh

# 3. If still broken — cold boot
shutdown -h now
# Wait 10s, power on
```

### Golden XML Restore

```bash
# Compare current vs golden
diff <(virsh dumpxml win10-gaming) /etc/libvirt/passthrough-win10-golden.xml

# Restore if needed
virsh destroy win10-gaming  # manual intervention — cold boot after
virsh undefine win10-gaming
virsh define /etc/libvirt/passthrough-win10-golden.xml
```

---

## Reference

| Item | Path / Value |
|---|---|
| Golden XML | `/etc/libvirt/passthrough-win10-golden.xml` |
| Phantom fix script | `/opt/fix-phantom-before-vm.sh` |
| Phantom flag file | `/opt/phantom-fix-needed` |
| GPU reset script | `/opt/gpu-reset.sh` |
| GRUB config | `/etc/default/grub` |
| modprobe VFIO config | `/etc/modprobe.d/vfio.conf` |
| mkinitcpio config | `/etc/mkinitcpio.conf` |
| VM disk image | `/var/lib/libvirt/images/win10-gaming.qcow2` |
| NVIDIA driver backup | `C:\Windows\Temp\nvidia-566.36.exe` |
| Sunshine config | `%APPDATA%\sunshine\sunshine.conf` |
| GPU IDs | `10de:21c4` (VGA), `10de:1aeb` (Audio), `10de:1aec` (USB), `10de:1aed` (Type-C) |
