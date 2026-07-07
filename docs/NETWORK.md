# Pipeline-Doc — NETWORK

## Topology
```
Router: 10.0.0.1 (XFINITY)
Subnet: 10.0.0.0/24
Gateway: 10.0.0.1
DNS: 1.1.1.1, 8.8.8.8

┌──────────────────────────────────────────────┐
│  ROUTER 10.0.0.1                             │
│                                              │
│  Port Forwards:                              │
│    32400 TCP → 10.0.0.201 (Plex remote)      │
│    8090  TCP → 10.0.0.201 (Dashboard)        │
│                                              │
│  ┌─────────────────────┐                     │
│  │ SERVER 10.0.0.201   │                     │
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
│  │ LAPTOP 10.0.0.234   │                     │
│  │ enp8s0 ONLY (WiFi   │                     │
│  │  DISABLED+MASKED)   │                     │
│  │ qBit: 8080(WebUI)   │                     │
│  │ gluetun: 51413(VPN) │                     │
│  └─────────────────────┘                     │
│                                              │
│  DESKTOP 10.0.0.192 (DHCP)                  │
└──────────────────────────────────────────────┘

VPN:
  Provider: AirVPN
  Protocol: WireGuard
  Endpoint: 184.75.214.165:1637
  Public IP: 184.75.208.10 (Toronto, Canada)
  VPN subnet: 10.153.205.171/32
  DNS: 10.128.0.1
  Killswitch: FIREWALL=on
  Ports forwarded through VPN: 51413 (torrent), 8080 (WebUI)
```

## SSH Configuration (~/.ssh/config)
```
Host server
  HostName 10.0.0.201
  Port 2223
  User topaz
  IdentityFile ~/.ssh/id_ed25519

Host laptop
  HostName 10.0.0.234
  Port 2225
  User laptop
  IdentityFile ~/.ssh/opencode_remote
```

## NFS
```
Server export: /mnt/20TB/homelab/media/downloads → 10.0.0.234
  Options: rw, sync, no_subtree_check, all_squash, anonuid=1000

Laptop mount: 10.0.0.201:/mnt/20TB/homelab/media/downloads → /mnt/server/downloads
  Options: nfs4, rw, vers=4.2, soft, timeo=10, retrans=2, async, noatime
```
