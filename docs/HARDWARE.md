# Hardware Specifications

## Server (APOS)

| Component | Specification |
|-----------|---------------|
| **CPU** | AMD Ryzen 7 5800X (8C/16T, 3.8 GHz) |
| **RAM** | 31 GB DDR4-3200 (4×8 GB Corsair) |
| **Kernel** | 6.8.0-134-generic |
| **Hostname** | apos |

### Storage

| Device | Capacity | Type | Mount |
|--------|----------|------|-------|
| `/dev/sdb2` | 120 GB | SSD | `/` (root) |
| `/dev/sda2` | 20 TB | HDD | data |
| `/dev/sdc2` | 8 TB | HDD | data |

### Network

| Interface | IP | Purpose |
|-----------|-----|---------|
| `enp8s0` | 10.0.0.200 | LAN primary |

### PCIe Layout

| Slot | Device | IOMMU Group | Notes |
|------|--------|-------------|-------|
| `03:00.1` | RTX 3090 Ti Audio | — | HDMI audio |

---


| Component | Specification |
|-----------|---------------|
| **CPU** | AMD Ryzen |
| **Audio** | Corsair HS55 Wireless (USB) |

### Network

| Interface | IP | Purpose |
|-----------|-----|---------|

---

## Laptop

| Component | Specification |
|-----------|---------------|
| **Model** | ThinkPad SL510 |
| **CPU** | Intel (no AVX2) |
| **Network** | IP 10.0.0.234 |
| **Hostname** | laptop |
