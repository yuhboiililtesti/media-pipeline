# Configuration Reference — Key System Files

## `/etc/default/grub`

```bash
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash intel_iommu=on iommu=pt video=efifb:off vfio-pci.ids=10de:2684,10de:22ba pcie_acs_override=downstream,multifunction rd.driver.pre=vfio-pci kvm.ignore_msrs=1"
```

| Parameter | Purpose |
|-----------|---------|
| `quiet splash` | Minimal boot output, show plymouth splash |
| `intel_iommu=on` | Enable Intel VT-d (required for VFIO passthrough) |
| `iommu=pt` | Passthrough mode — only IOMMU-translate devices assigned to VMs (reduces overhead on host devices) |
| `video=efifb:off` | Disable EFI framebuffer on the GPU being passed through (prevents host from binding it) |
| `vfio-pci.ids=10de:2684,10de:22ba` | Bind NVIDIA GPU (2684) and its audio function (22ba) to `vfio-pci` at boot — prevents nvidia/nouveau from claiming them |
| `pcie_acs_override=downstream,multifunction` | Force ACS separation for IOMMU groups (can split GPU into isolated groups if motherboard BIOS lacks proper ACS) |
| `rd.driver.pre=vfio-pci` | Load `vfio-pci` early in initramfs — ensures it claims devices before the native drivers |
| `kvm.ignore_msrs=1` | Ignore unknown Model-Specific Register access (silences kernel warnings from Windows guests) |

> After editing, run: `sudo update-grub && sudo update-initramfs -u -k all`

---

## `/etc/modprobe.d/vfio.conf`

```conf
# VFIO passthrough — bind NVIDIA GPU to vfio-pci at boot
options vfio-pci ids=10de:2684,10de:22ba
softdep nvidia pre: vfio-pci
softdep nouveau pre: vfio-pci
softdep drm pre: vfio-pci
```

| Line | Purpose |
|------|---------|
| `options vfio-pci ids=...` | Tells the `vfio-pci` kernel module which PCI device IDs to claim |
| `softdep nvidia pre: vfio-pci` | Ensures `vfio-pci` loads before `nvidia` — if nvidia loads first, it claims the GPU and VFIO cannot |
| `softdep nouveau pre: vfio-pci` | Same protection against the open-source `nouveau` driver |
| `softdep drm pre: vfio-pci` | Ensures the DRM subsystem doesn't grab the GPU framebuffer |

> The `ids=` here must match the `vfio-pci.ids=` in GRUB.

---

## `/etc/initramfs-tools/modules`

```conf
vfio
vfio_iommu_type1
vfio_pci
vfio_virqfd
```

| Module | Purpose |
|--------|---------|
| `vfio` | Core VFIO framework |
| `vfio_iommu_type1` | IOMMU driver for VFIO |
| `vfio_pci` | PCI device assignment driver |
| `vfio_virqfd` | Virtual IRQ support |

These modules are loaded **before** the root filesystem mounts, ensuring the GPU is isolated before any display manager or NVIDIA driver initializes.

---

## `/etc/libvirt/passthrough-win10-golden.xml`

Key sections of the libvirt domain XML:

### vCPU

```xml
<vcpu placement="static">8</vcpu>
<cputune>
  <vcpupin vcpu="0" cpuset="6"/>
  <vcpupin vcpu="1" cpuset="14"/>
  <vcpupin vcpu="2" cpuset="7"/>
  <vcpupin vcpu="3" cpuset="15"/>
  <vcpupin vcpu="4" cpuset="8"/>
  <vcpupin vcpu="5" cpuset="16"/>
  <vcpupin vcpu="6" cpuset="9"/>
  <vcpupin vcpu="7" cpuset="17"/>
</cputune>
```

Each vCPU is pinned to a specific physical core (matching thread pairs on a hyperthreaded 8-core CPU: cores 6-9, threads 14-17).

### Memory

```xml
<memory unit="KiB">12582912</memory>
<currentMemory unit="KiB">12582912</currentMemory>
<memoryBacking>
  <hugepages/>
</memoryBacking>
```

12 GB of RAM backed by hugepages (2 MB pages for reduced TLB overhead).

### CPU Topology

```xml
<cpu mode="host-passthrough" check="none">
  <topology sockets="1" dies="1" cores="4" threads="2"/>
  <feature policy="require" name="invtsc"/>
  <feature policy="require" name="topoext"/>
</cpu>
```

Passes through the host CPU (CachyOS-optimized kernel), presents a topology matching the physical core/thread layout, and exposes `invariant TSC` for stable timing.

### GPU Passthrough (hostdev)

```xml
<hostdev mode="subsystem" type="pci" managed="yes">
  <source>
    <address domain="0x0000" bus="0x01" slot="0x00" function="0x0"/>
  </source>
  <rom bar="on" file="/var/lib/libvirt/vbios/rtx4060.rom"/>
  <address type="pci" domain="0x0000" bus="0x06" slot="0x00" function="0x0"/>
</hostdev>
<hostdev mode="subsystem" type="pci" managed="yes">
  <source>
    <address domain="0x0000" bus="0x01" slot="0x00" function="0x1"/>
  </source>
  <address type="pci" domain="0x0000" bus="0x07" slot="0x00" function="0x0"/>
</hostdev>
```

Both GPU (function 0) and HDMI audio (function 1) are assigned. A patched VBIOS ROM (`rtx4060.rom`) is supplied for proper UEFI boot.

### Video

```xml
<video>
  <model type="none"/>
</video>
```

No virtual GPU — display is via the physical GPU output only.

### Network

```xml
<interface type="bridge">
  <mac address="52:54:00:aa:bb:cc"/>
  <source bridge="br0"/>
  <model type="virtio"/>
</interface>
```

VirtIO network bridge connecting the VM to the host's `br0` (bridged to physical LAN).

---

## `/etc/systemd/system/gaming-vm.service`

```ini
[Unit]
Description=Windows 11 Gaming VM
After=network.target libvirtd.service
Requires=libvirtd.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/virsh start win10
ExecStop=/usr/bin/virsh shutdown win10
ExecStop=/bin/sleep 30
ExecStop=/usr/bin/virsh destroy win10
User=topaz
Group=libvirt

[Install]
WantedBy=multi-user.target
```

| Field | Purpose |
|-------|---------|
| `After=libvirtd.service` | Ensures libvirt is running before starting VM |
| `Type=oneshot` | Service completes after start action |
| `RemainAfterExit=yes` | Keeps service "active" so stop is recognized |
| `ExecStop` chain | Graceful shutdown (30s), then force-destroy if hung |
| `User=topaz` | Runs as non-root with libvirt group permissions |

### Usage

```bash
sudo systemctl start gaming-vm     # Start VM
sudo systemctl stop gaming-vm      # Graceful shutdown (30s then destroy)
sudo systemctl enable gaming-vm    # Auto-start at boot
virsh list --all                   # Check VM state
```

---

## `/etc/udev/rules.d/99-kvm.rules`

```conf
# Set correct group and permissions for KVM device
KERNEL=="kvm", GROUP="kvm", MODE="0660"

# Set group for VFIO devices
SUBSYSTEM=="vfio", OWNER="root", GROUP="kvm", MODE="0660"

# Bind NVIDIA GPU devices to vfio-pci at boot
SUBSYSTEM=="pci", ATTRS{vendor}=="0x10de", ATTRS{device}=="0x2684", DRIVER=="vfio-pci"
SUBSYSTEM=="pci", ATTRS{vendor}=="0x10de", ATTRS{device}=="0x22ba", DRIVER=="vfio-pci"
```

| Rule | Purpose |
|------|---------|
| `/dev/kvm` permissions | Allows `kvm` group members to use KVM without sudo |
| VFIO device ownership | Ensures created VFIO devices are accessible |
| GPU device binding | Confirms NVIDIA devices are bound to `vfio-pci` driver at hotplug/reboot |

```bash
# Apply after editing
sudo udevadm control --reload-rules
sudo udevadm trigger
```

---

## `/mnt/20TB/homelab/media/compose/docker-compose.yml`

### Service Listing

| Service | Image | Ports | Volumes |
|---------|-------|-------|---------|
| sonarr | `linuxserver/sonarr:latest` | `8989` | `/mnt/20TB/homelab/media/config/sonarr`, `/mnt/20TB/homelab/media` |
| radarr | `linuxserver/radarr:latest` | `7878` | `/mnt/20TB/homelab/media/config/radarr`, `/mnt/20TB/homelab/media` |
| prowlarr | `linuxserver/prowlarr:latest` | `9696` | `/mnt/20TB/homelab/media/config/prowlarr` |
| qbittorrent | `linuxserver/qbittorrent:latest` | `8081`, `6881/udp` | `/mnt/20TB/homelab/media/config/qbit`, `/mnt/20TB/homelab/media/downloads` |
| tdarr | `haveagitgat/tdarr:latest` | `8265`, `8266` | `/mnt/20TB/homelab/media`, `/mnt/20TB/homelab/media/tdarr/cache` |
| overseerr | `sctx/overseerr:latest` | `5055` | `/mnt/20TB/homelab/media/config/overseerr` |
| plex | `linuxserver/plex:latest` | `32400` | `/mnt/20TB/homelab/media/config/plex`, `/mnt/20TB/homelab/media` |
| immich | `ghcr.io/immich-app/immich-server:release` | `2283` | `/mnt/20TB/homelab/media/immich`, `/mnt/20TB/photos` |
| decluttarr | `ghcr.io/decluttarr/decluttarr:latest` | — | `/mnt/20TB/homelab/media/compose/decluttarr/config.yaml` |

All services share the custom network `media-net` and are behind a Traefik reverse proxy on the server (not directly exposed beyond LAN).

---

## `/mnt/20TB/homelab/media/compose/decluttarr/config.yaml`

```yaml
# Decluttarr — Media stack cleanup automation
# Repository: https://github.com/decluttarr/decluttarr

---

### GENERAL ###
debug: false
sleep_timer: 30              # Seconds between loops
remove_timers: false
remove_failed_imports: true  # Remove "failed to import" items from Sonarr/Radarr
remove_missing: true         # Remove series/movies with all files deleted from disk
remove_stalled_downloads: true
remove_orphans: false
remove_unmonitored: false
permitted_statuses: []
check_existence: false
check_extension: true

### SONARR (TV) ###
sonarr:
  - url: "http://sonarr:8989"
    apikey: "SONARR_API_KEY"
    verify_ssl: false
    filters:
      stalled_downloads: true
      failed_imports: true
      missing_downloads: true
      missing_files: true

### RADARR (Movies) ###
radarr:
  - url: "http://radarr:7878"
    apikey: "RADARR_API_KEY"
    verify_ssl: false
    filters:
      stalled_downloads: true
      failed_imports: true
      missing_downloads: true
      missing_files: true
      grab_404: false

### QBITTORRENT ###
qbittorrent:
  - url: "http://qbittorrent:8081"
    username: "topaz"
    password: "USER_PASSWORD"
    ignore_private_trackers: false
    auto_tmm: false

### CACHE TRACKING ###
cache_tracker:
  - paths:
      - "/mnt/20TB/homelab/media/downloads"
    days_to_keep: 7          # Remove downloads older than 7 days
    interval: 360            # Check every 6 hours
```

---

## CachyOS Configuration Files

### `~/.config/plasma-workspace/env/nvidia-wayland.sh`

```bash
#!/bin/sh
# Enable NVIDIA Wayland support in KDE Plasma
export KWIN_DRM_USE_EGL_STREAMS=0
export KWIN_DRM_NO_AMS=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export GBM_BACKEND=nvidia-drm
export __GL_VRR_ALLOWED=1
export WLR_NO_HARDWARE_CURSORS=1
```

| Variable | Purpose |
|----------|---------|
| `KWIN_DRM_USE_EGL_STREAMS=0` | Force GBM instead of EGLStreams (better Wayland support on recent NVIDIA drivers) |
| `KWIN_DRM_NO_AMS=1` | Disable Atomic Mode Setting (workaround for NVIDIA flickering) |
| `__GLX_VENDOR_LIBRARY_NAME=nvidia` | Use NVIDIA GLX library |
| `GBM_BACKEND=nvidia-drm` | Use NVIDIA's GBM backend for DRM buffer allocation |
| `__GL_VRR_ALLOWED=1` | Enable Variable Refresh Rate (G-Sync/FreeSync) |
| `WLR_NO_HARDWARE_CURSORS=1` | Disable hardware cursor (fixes cursor rendering glitches on NVIDIA) |

### `~/.config/autostart/plasmashell-watchdog.desktop`

```ini
[Desktop Entry]
Type=Application
Name=Plasmashell Watchdog
Comment=Restart plasmashell if it crashes
Exec=/bin/bash -c 'while true; do plasmashell --replace &> /dev/null; sleep 10; done'
X-KDE-autostart-phase=2
NoDisplay=true
```

Keeps `plasmashell` alive — restarts it automatically if it exits (common issue with NVIDIA Wayland).

### `~/.config/kwinrc` (relevant sections)

```ini
[Windows]
FocusPolicy=ClickToFocus
NextFocusPrefersPointer=true
SeparateScreenFocus=false
ActiveMouseScreen=true

[Wayland]
VirtualKeyboardEnabled=false

[Compositing]
OpenGLIsUnsafe=false
Backend=OpenGL
GLCore=false
GLPreferBufferSwap=a
GLTextureFilter=1
Enabled=true
```

### `~/.config/kcminputrc` (cursor)

```ini
[Mouse]
Acceleration=0
AccelerationProfile=0
CursorTheme=breeze_cursors
XLbInptAccelProfileFlat=false
```

Cursor acceleration is set to `0` (flat) for precise control during remote streaming and gaming.

---

## File Permissions Overview

| File | Owner | Mode | Reason |
|------|-------|------|--------|
| `/etc/default/grub` | root | 644 | Readable, generated by grub-mkconfig |
| `/etc/modprobe.d/vfio.conf` | root | 644 | Readable for modprobe |
| `/etc/initramfs-tools/modules` | root | 644 | Readable for mkinitcpio/update-initramfs |
| `/etc/libvirt/passthrough-win10-golden.xml` | root | 600 | Contains device paths, sensitive |
| `/etc/systemd/system/gaming-vm.service` | root | 644 | Standard systemd unit |
| `/etc/udev/rules.d/99-kvm.rules` | root | 644 | udev reads these on trigger |
| `config.json` | root | 600 | Contains secrets |
| `nvidia-wayland.sh` | topaz | 755 | Sourced by Plasma workspace env |
