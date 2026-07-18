# NETWORK — Complete Reference
# Updated: 2026-07-14

---

## TOPOLOGY

```
ROUTER 10.0.0.1 (XFINITY)
Subnet: 10.0.0.0/24
Gateway: 10.0.0.1
DNS: 1.1.1.1, 8.8.8.8

┌─────────────────────────────────────────────────────┐
│  SERVER 10.0.0.200                                  │
│  NIC: enp10s0                                       │
│  SSH: 2223 (key-based, password disabled)           │
│  Firewall: nftables (policy DROP) + UFW             │
│  VPN: AirVPN WireGuard (173.249.217.19 NYC)        │
├─────────────────────────────────────────────────────┤
│  LAPTOP 10.0.0.192                                  │
│  NIC: enp8s0 (ethernet ONLY, static)                │
│  SSH: 2224                                          │
│  Services: Kuma (:3001), Heimdall (:8080)          │
├─────────────────────────────────────────────────────┤
│  DESKTOP 10.0.0.234                                 │
│  OS: CachyOS (Arch-based)                           │
│  GPU: RTX 3080                                      │
│  VPN: AirVPN WireGuard (separate instance)          │
│  Client: Moonlight (streams gaming VM)              │
└─────────────────────────────────────────────────────┘
```

---

## FIREWALL (nftables + UFW)

UFW is active but nftables does the actual packet filtering.
nftables has `policy drop` — only explicitly allowed ports pass.

fix-nftables.service flushes and rebuilds rules on boot.

All ports restricted to 10.0.0.0/24 (LAN) except SSH.

### Open TCP Ports
22, 2223 (SSH), 139, 445 (SMB), 32400 (Plex), 7474 (Autobrr),
7878 (Radarr), 8083 (qBit WebUI), 8191 (FlareSolverr — localhost only),
8265, 8266 (Tdarr), 8989 (Sonarr), 9696 (Prowlarr), 5055 (Overseerr),
51414 (qBit torrent), 6767 (Bazarr), 2468 (Cross-seed), 4330 (Libvirt),
5900 (SPICE), 2283 (Immich), 9090 (libvirt guest),
44321-44323 (Libvirt metrics)

### Open UDP Ports
137, 138 (NetBIOS), 51414 (qBit torrent)

---

## SSH CONFIGURATION

### Server (10.0.0.200:2223)
```
Host server
  HostName 10.0.0.200
  Port 2223
  User topaz
  IdentityFile ~/.ssh/server_ed25519
```

### Laptop (10.0.0.192:2224)
```
Host laptop
  HostName 10.0.0.192
  Port 2224
  User topaz
```

### Desktop (10.0.0.234)
```
Host desktop
  HostName 10.0.0.234
  User topaz
```

---

## SAMBA SHARES

| Share         | Path                | Access       | Writable |
|---------------|---------------------|--------------|----------|
| server-20TB   | /mnt/20TB           | topaz        | yes      |
| server-8TB    | /mnt/8TB            | topaz        | yes      |
| topaz-home    | /home/topaz         | topaz        | yes      |
| server-root   | /                   | topaz        | no (ro)  |

CIFS credentials: /etc/samba/creds-server (username=topaz, password=USER_PASSWORD)

### CachyOS Mounts (in /etc/fstab)
```
//10.0.0.200/server-20TB  /mnt/server-20TB  cifs  credentials=/etc/samba/creds-server,uid=1000,gid=1000  0  0
//10.0.0.200/server-8TB   /mnt/server-8TB   cifs  credentials=/etc/samba/creds-server,uid=1000,gid=1000  0  0
```

---

## VPN (AirVPN WireGuard)

### Server
- Endpoint: 198.44.136.238:1637 (NYC)
- VPN IP: 10.147.17.165/32
- Public IP: 173.249.217.19
- DNS: 1.1.1.1
- Keys: stored in /mnt/20TB/homelab/media/compose/.env (perms 600)
- Forwarded ports: 51414 (torrent)

### Desktop
- Separate AirVPN WireGuard instance (not routing through server)
- Used for personal browsing
- VPN subnet: 10.153.205.171/32

---

## NIC TUNING

- Power saving: disabled
- TCP keepalive: 60s interval, 10s probe interval, 6 probes
- Wake-on-LAN: enabled (enp10s0)
- vm.swappiness: 10
