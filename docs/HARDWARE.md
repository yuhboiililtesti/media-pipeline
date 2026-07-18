# Hardware Specifications

## Server (APOS)

| Component | Specification |
|-----------|---------------|
| **CPU** | AMD Ryzen 7 5800X (8C/16T, 3.8 GHz) |
| **RAM** | 31 GB DDR4-3200 (4×8 GB Corsair) |
| **GPU1** | NVIDIA RTX 3090 Ti 24 GB (host GPU, driver 580.159.03) |
| **GPU2** | NVIDIA GTX 1660 SUPER 6 GB (vfio-pci passthrough to VM) |
| **Kernel** | 6.8.0-134-generic |
| **Hostname** | apos |

### Storage

| Device | Capacity | Type | Mount |
|--------|----------|------|-------|
| `/dev/sdb2` | 120 GB | SSD | `/` (root) |
| `/dev/sda2` | 20 TB | HDD | data |
| `/dev/sdc2` | 8 TB | HDD | data |
| `/dev/nvme0n1` | 2 TB | NVMe | fast storage |

### Network

| Interface | IP | Purpose |
|-----------|-----|---------|
| `enp8s0` | 10.0.0.200 | LAN primary |

### PCIe Layout

| Slot | Device | IOMMU Group | Notes |
|------|--------|-------------|-------|
| `03:00.0` | RTX 3090 Ti | own group | Host GPU |
| `03:00.1` | RTX 3090 Ti Audio | — | HDMI audio |
| `0b:00.0` | GTX 1660 SUPER VGA | own group | VM passthrough |
| `0b:00.1` | GTX 1660 SUPER Audio | own group | VM passthrough |
| `0b:00.2` | GTX 1660 SUPER USB-C | own group | VM passthrough |
| `0b:00.3` | GTX 1660 SUPER Serial | own group | VM passthrough |

---

## CachyOS Desktop

| Component | Specification |
|-----------|---------------|
| **CPU** | AMD Ryzen |
| **GPU** | NVIDIA RTX 3080 (driver 610.43.03) |
| **Display** | 1920×1080 @ 240 Hz, Wayland |
| **Audio** | Corsair HS55 Wireless (USB) |
| **DE/WM** | KDE Plasma 6.7.2 / KWin 6.7.2 |
| **Hostname** | desktop |

### Network

| Interface | IP | Purpose |
|-----------|-----|---------|
| `enp8s0` | 10.0.0.192 | LAN primary |

---

## Laptop

| Component | Specification |
|-----------|---------------|
| **Model** | ThinkPad SL510 |
| **CPU** | Intel (no AVX2) |
| **Network** | IP 10.0.0.234 |
| **Hostname** | laptop |
