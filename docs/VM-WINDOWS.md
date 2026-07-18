# Windows VM — OS & Monitoring

## System Info

| Field | Value |
|-------|-------|
| OS | Windows 11 Pro |
| Build | 22631 |
| Hostname | DESKTOP-5AU9FBV |
| vCPUs | 8 |
| RAM | 12 GB |
| Disk | 1 TB (virtio, resized 2026-07-14) |
| Activation | Digital license tied to VM UUID |

---

## NVIDIA Driver

| Field | Value |
|-------|-------|
| Active version | 560.94 (32.0.15.6094) |
| INF | oem17.inf |
| Device Manager status | OK — no error 43 |
| GPU | NVIDIA GeForce RTX (passthrough) |

### Version Policy

Version **560.94** is intentionally kept rather than upgrading:

| Reason | Detail |
|--------|--------|
| Stability | 560.94 has zero issues with the RMForceDisplay workaround |
| Compatibility | Newer drivers (565+) have been reported to break VFIO passthrough |
| Proven | Months of uptime across reboots with no GPU dropouts |

### Backup Driver

```
C:\Windows\Temp\nvidia-566.36.exe  (699 MB, original installer)
```

This is the next candidate version. It is **not** installed — kept as a fallback and for reference. The file is the stock NVIDIA Game Ready driver downloaded from nvidia.com.

### Driver Management Quick Reference

| Action | Method |
|--------|--------|
| **List driver store packages** | `pnputil /enum-drivers` (look for oem*.inf with NVIDIA) |
| **Remove old driver** | `pnputil /delete-driver oemXX.inf /uninstall` |
| **Roll back** | Device Manager → Display Adapters → RTX → Driver tab → Roll Back Driver |
| **Silent install** | `setup.exe -s` (does **not** work with DCH drivers — use GUI `setup.exe`) |
| **Clean install** | Use DDU in Safe Mode, then GUI install 560.94 |

> DCH drivers require the NVIDIA Control Panel from the Microsoft Store. Silent/unattended flags (`-s`, `-n`) are ignored. Use the standard GUI installer instead.

---

## Sunshine (Streaming Server)

### Config

| Field | Value |
|-------|-------|
| Config path | `C:\Program Files\Sunshine\config\sunshine.conf` |
| Encoder | `nvenc` |
| Preset | `p3` (P3 — fast/balanced) |
| Two-pass | `quarter_res` |
| HEVC B-frames | Disabled (`hevc_b_frames = 0`) |
| Resolution | Native (output follows client request) |
| FPS | 60 |

### Service

| Field | Value |
|-------|-------|
| Service name | `Sunshine` |
| Startup | Automatic |
| Status | Running |
| Log | `C:\Program Files\Sunshine\config\sunshine.log` |

### Access

| Method | Address |
|--------|---------|
| Web UI | `http://localhost:47990` |
| Streaming port | TCP 47989 (Moonlight) |
| HTTPS | TCP 47984 |
| Remote (via server NAT) | `10.0.0.200:47989` / `10.0.0.200:47984` |

---

## Windows Tuning

All items below are **confirmed applied** and persist across reboots.

### Power & Performance

| Setting | Value | Where |
|---------|-------|-------|
| Power plan | **High Performance** | Settings → Power |
| GPU scheduling | **ON** | Settings → Display → Graphics |
| Display timeout | **Never** | Settings → Power |
| Sleep | **Never** | Settings → Power |

### Input

| Setting | Value | Where |
|---------|-------|-------|
| Mouse acceleration | **OFF** (Enhanced Pointer Precision unchecked) | Mouse settings |

### Visual & UI

| Setting | Value |
|---------|-------|
| Visual effects | OFF (`SystemPropertiesPerformance` → Adjust for best performance) |
| Transparency effects | OFF |
| Animations | OFF (`Accessibility` → Animation effects disabled) |
| Taskbar animations | OFF |
| Window snap/aero shake | OFF |

### Services Disabled

| Service | Display Name | Reason |
|---------|-------------|--------|
| `XblAuthManager` | Xbox Live Auth Manager | Xbox overlay |
| `XblGameSave` | Xbox Live Game Save | Unused |
| `XboxNetApiSvc` | Xbox Live Networking | Unused |
| `XboxGipSvc` | Xbox Accessory Management | Unused |
| `WSearch` | Windows Search | Disk I/O reduction |
| `SysMain` | SysMain (Superfetch) | Unnecessary with SSD |
| `DiagTrack` | Connected User Experiences & Telemetry | Privacy, resource saving |
| `DusmSvc` | Data Usage | Telemetry |

---

## SSH Access

| Field | Value |
|-------|-------|
| Software | OpenSSH Server (built-in optional feature) |
| Port | **2225** |
| User | `topaz` |
| Password | `USER_PASSWORD` |
| Shell | PowerShell |

### Remote Access Path

```
Client → Server (10.0.0.200) iptables DNAT port 2225 → VM IP port 2225
```

The server runs an `iptables` DNAT rule forwarding TCP 2225 traffic to the Windows VM's internal IP.

### Connect

```bash
ssh -p 2225 topaz@10.0.0.200
```

---

## Scheduled Tasks

### GPUForceActive

| Field | Value |
|-------|-------|
| Task name | `GPUForceActive` |
| Trigger | At system startup |
| Run as | SYSTEM |
| Privileges | Run with highest privileges |
| Action | `C:\Users\topaz\gpu-fix.bat` |

#### gpu-fix.bat

```bat
@echo off
REM Force NVIDIA GPU to remain active after driver load
REM Prevents error 43 / device disappearing from device manager
devcon.exe restart "PCI\VEN_10DE*"
```

> This task ensures the GPU is reinitialized on every boot before Sunshine starts,
> working around the RMForceDisplay device state issue.

---

## Security Scan

| Field | Value |
|-------|-------|
| Script path | `C:\Windows\Temp\security-scan.ps1` |
| Sections | 12 |
| Execution | As Administrator in PowerShell |
| Alias | `vm sec` (from server SSH, triggers remote execution) |

### Sections

| # | Section | Checks |
|---|---------|--------|
| 1 | System Info | OS version, build, hostname, uptime |
| 2 | Network | Listening ports, active connections, firewall profiles |
| 3 | DNS | Resolution tests, DNS server config |
| 4 | Processes | Running processes, suspicious names, high CPU |
| 5 | Persistence | Startup entries, registry Run keys |
| 6 | Scheduled Tasks | All tasks, last run, triggers |
| 7 | Local Accounts | User list, group memberships, admin count |
| 8 | Firewall Rules | All inbound/outbound rules, port 2225, Sunshine ports |
| 9 | Defender | Status, last scan, exclusions |
| 10 | Software | Installed programs, version list |
| 11 | Events | Security log (last 24h), System log errors |
| 12 | Integrity | Sunshine config hash, gpu-fix.bat hash |

### Run

```bash
# From server SSH
vm sec

# Or from Windows directly (Admin PowerShell)
powershell -ExecutionPolicy Bypass -File C:\Windows\Temp\security-scan.ps1
```

---

## Driver Management — Detailed

### Listing Drivers in the Store

```powershell
pnputil /enum-drivers | Select-String -Pattern "NVIDIA|oem"
```

### Rollback Procedure

1. **Open Device Manager** (`devmgmt.msc`)
2. Expand **Display Adapters**
3. Right-click **NVIDIA GeForce RTX** → **Properties**
4. **Driver** tab → **Roll Back Driver**
5. Reboot

### Manual Driver Swap (Fallback)

```powershell
# Remove current driver
pnputil /delete-driver oem17.inf /uninstall
# Reboot
shutdown /r /t 0
# After reboot, install new driver via GUI
C:\Windows\Temp\nvidia-566.36.exe
```

### Driver Store Cleanup

```powershell
# View all driver packages
pnputil /enum-drivers

# Remove unused old drivers
pnputil /delete-driver oemXX.inf
```

> **Warning:** Do not delete `oem17.inf` (active 560.94) unless you have a replacement staged.

---

## Quick Reference

| Task | Command / Action |
|------|-----------------|
| Restart Sunshine | `Restart-Service Sunshine` |
| Check GPU | `nvidia-smi` (from CMD) |
| View Sunshine log | `Get-Content .\sunshine.log -Tail 50` |
| Check Defender | `Get-MpComputerStatus` |
| List scheduled tasks | `Get-ScheduledTask | ? TaskName -like "*GPU*"` |
| Reboot VM | `shutdown /r /t 0` |
| VM status from server | `vm health` (server alias) |
| Security scan from server | `vm sec` (server alias) |
| RDP | `xfreerdp /v:VM_IP /u:topaz` (internal network) |
