# Pipeline-Doc — NETWORK

## Topology
```
Router: <router-ip> (XFINITY)
Subnet: 10.0.0.0/24
Gateway: <router-ip>
DNS: 1.1.1.1, 8.8.8.8

┌──────────────────────────────────────────────┐
│  ROUTER <router-ip>                             │
│                                              │
│  Port Forwards:                              │
│    32400 TCP → <server-ip> (Plex remote)      │
│    8090  TCP → <server-ip> (Dashboard)        │
│                                              │
│  ┌─────────────────────┐                     │
│  │ SERVER <server-ip>   │                     │
│  │ enp6s0f0            │                     │
│  │ UFW: deny in, allow │                     │
│  │  out                │                     │
│  │ Ports: 2223(SSH)    │                     │
│  │  32400(Plex)        │                     │
│  │  111+2049(NFS→.234) │                     │
│  │  8090(Dashboard)    │                     │
│  │  137-139,445(SMB)   │                     │
│  └────────┬────────────┘                     │
│           │ LAN                               │
│  ┌────────┴────────────┐                     │
│  │ LAPTOP <laptop-ip>   │                     │
│  │ enp8s0 ONLY (WiFi   │                     │
│  │  DISABLED+MASKED)   │                     │
│  │ qBit: 8080(WebUI)   │                     │
│  │ gluetun: 51413(VPN) │                     │
│  └─────────────────────┘                     │
│                                              │
│  DESKTOP <desktop-ip> (DHCP)                  │
└──────────────────────────────────────────────┘

VPN:
  Provider: AirVPN
  Protocol: WireGuard
  Endpoint: <vpn-public-ip>:1637
  Public IP: <vpn-public-ip> (Toronto, Canada)
  VPN subnet: 10.153.205.171/32
  DNS: 10.128.0.1
  Killswitch: FIREWALL=on
  Ports forwarded through VPN: 51413 (torrent), 8080 (WebUI)
```

## SSH Configuration (~/.ssh/config)
```
Host server
  HostName <server-ip>
  Port 2223
  User topaz
  IdentityFile ~/.ssh/id_ed25519

Host laptop
  HostName <laptop-ip>
  Port 2225
  User laptop
  IdentityFile ~/.ssh/opencode_remote
```

## NFS
```
Server export: /mnt/20TB/homelab/media/downloads → <laptop-ip>
  Options: rw, sync, no_subtree_check, all_squash, anonuid=1000

Laptop mount: <server-ip>:/mnt/20TB/homelab/media/downloads → /mnt/server/downloads
  Options: nfs4, rw, vers=4.2, soft, timeo=10, retrans=2, async, noatime
```
