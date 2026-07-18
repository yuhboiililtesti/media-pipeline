# MASTER — Homelab Documentation Index

## Systems
| System | IP | OS | GPU | Role |
|--------|-----|-----|-----|------|
| APOS (server) | 10.0.0.200 | Ubuntu 24.04 | RTX 3090 Ti + GTX 1660 SUPER | Server, pipeline, VM host |
| Cachy | 10.0.0.192 | CachyOS | RTX 3080 | Gaming desktop, Moonlight client |
| Laptop | 10.0.0.234 | Ubuntu | Intel iGPU | Monitoring, dashboard |

## Access
```
SSH Server:   ssh -p 2223 topaz@10.0.0.200
SSH Windows:  ssh -p 2225 topaz@10.0.0.200
SSH Laptop:   ssh -p 2225 laptop@10.0.0.234
All passwords: USER_PASSWORD
```

## Documentation Files
| File | Content |
|------|---------|
| MASTER.md | This index |
| ARCHITECTURE.md | Full system architecture, network map, data flow |
| HARDWARE.md | All hardware specs across all systems |
| SERVICES.md | Every service, port, container, process |
| NETWORK.md | VPN, subnets, iptables, port forwarding |
| AUTOMATION.md | Cron jobs, systemd services, auto-start chain |
| VM-GPU.md | GPU passthrough, phantom fix, NVENC, QEMU config |
| VM-WINDOWS.md | Windows VM OS config, drivers, tuning, SSH |
| PIPELINE.md | Docker compose, media stack, download flow |
| CACHYOS.md | CachyOS desktop, Wayland fix, Moonlight, SSH |
| LAPTOP.md | Satellite monitoring, health checks, Heimdall |
| COMMANDS.md | All useful commands, quick reference |
| ISSUES-SOLUTIONS.md | Every issue encountered and how to fix it |
| RECOVERY.md | Emergency procedures, reboot sequences, backups |
| API-REFERENCE.md | API keys, tokens, credentials reference |
| CONFIG.md | Key config file locations and contents |
| HEALTH.md | Health scan scripts, monitoring, checks |
