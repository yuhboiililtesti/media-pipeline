# QBITTORRENT TUNING — Complete Reference

## Connection
```
URL:      http://<laptop-ip>:8080
Username: topaz
Password: (see /home/topaz/home/info)
```

## Current Settings (Laptop — Dual-core, 3.7GB RAM)
```
Active DL:       15        Max torrents:      200
Active UL:       15        Disk cache:        1536 MB
Disk queue:      32 MB     File pool:         10000
Connections:     5000      Per torrent:       500
Socket backlog:  3000      Half-open:         400
Port:            51413     Encryption:        required
Preallocation:   enabled   DHT/PEX/LSD:       enabled
Queueing:        enabled   Announce all:      enabled
Refresh interval: 800ms    Re-announce:       enabled

Save path:       /downloads/ → NFS → server /mnt/20TB/homelab/media/downloads/
Temp path:       /downloads/incomplete/
Categories:      radarr, sonarr
```

## Docker Limits
```
CPU:  2 cores max, 1 core reserved
RAM:  3.5 GB max, 1.5 GB reserved
Network: gluetun (VPN killswitch)
```

## VPN
```
Provider:    AirVPN (WireGuard)
Endpoint:    <vpn-public-ip>:1637
Public IP:   <vpn-public-ip> (Toronto)
Killswitch:  FIREWALL=on
Port:        51413 (torrent), 8080 (WebUI)
Local:       FIREWALL_INPUT_PORTS=8080
```

## Tracker Injection (37 public trackers)
```
udp://tracker.opentrackr.org:1337/announce
udp://open.stealth.si:80/announce
udp://tracker.torrent.eu.org:451/announce
udp://explodie.org:6969/announce
udp://tracker.coppersurfer.tk:6969/announce
udp://9.rarbg.to:2710/announce
udp://tracker.internetwarriors.net:1337/announce
udp://ipv4.tracker.harry.lu:80/announce
http://tracker.opentrackr.org:1337/announce
udp://tracker.leechers-paradise.org:6969/announce
udp://tracker.openbittorrent.com:6969/announce
udp://open.demonii.com:1337/announce
udp://tracker.moeking.me:6969/announce
udp://tracker.bitsearch.to:1337/announce
udp://tracker.tiny-vps.com:6969/announce
udp://p4p.arenabg.com:1337/announce
udp://movies.zsw.ca:6969/announce
udp://retracker.lanta-net.ru:2710/announce
udp://bt1.archive.org:6969/announce
udp://bt2.archive.org:6969/announce
udp://tracker.dler.com:6969/announce
udp://tracker.altrosky.nl:6969/announce
udp://tracker.auctor.tv:6969/announce
udp://tracker.birkenwald.de:6969/announce
udp://tracker.breizh.pm:6969/announce
udp://tracker.edkj.club:6969/announce
udp://tracker.srv00.com:6969/announce
udp://tracker.swateam.org.uk:2710/announce
udp://tracker.tasvideos.org:6969/announce
udp://tracker.theoks.net:6969/announce
udp://trackerb.jonaslsa.com:6969/announce
udp://tracker1.bt.moack.co.kr:80/announce
http://tracker.bt4g.com:2095/announce
http://tracker.files.fm:6969/announce
http://tracker.gbitt.info:80/announce
http://open.acgnxtracker.com:80/announce
wss://tracker.openwebtorrent.com:443/announce
```

## Tuning History
```
v1: DL:18, Tor:500, Cache:1024MB — baseline
v2: DL:22, Tor:650, Cache:2048MB — pushed harder
v3: DL:28, Tor:800, Cache:2560MB — maxed out (caused laptop crash at 2104 torrents)
v4: DL:15, Tor:200, Cache:1536MB — safe limits for dual-core 3.7GB
```

## LAN Protection
```
bypass_local_auth: true
bypass_auth_subnet_whitelist: <local-ip>/8,192.168.0.0/16,172.16.0.0/12
No more IP bans from Radarr/Sonarr auth attempts
```
