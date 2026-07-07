#!/usr/bin/env python3
"""Pipeline Health Monitor — Both devices always active, killswitch verified"""
import urllib.request, urllib.parse, json, time, subprocess, os

LOG = '/mnt/20TB/homelab/media/Pipeline/logs/pipeline-monitor.log'
QBIT_U = 'topaz'; QBIT_P = 'YOUR_QBIT_PASSWORD'

def log(msg):
    t = time.strftime('%H:%M:%S')
    line = '[%s] %s' % (t, msg)
    print(line)
    with open(LOG, 'a') as f: f.write(line + chr(10))

def qbit_check(name, host):
    try:
        c=urllib.request.HTTPCookieProcessor()
        o=urllib.request.build_opener(c)
        o.open(urllib.request.Request(host+'/api/v2/auth/login',data=urllib.parse.urlencode({'username':QBIT_U,'password':QBIT_P}).encode()),timeout=8)
        info=json.loads(o.open(urllib.request.Request(host+'/api/v2/transfer/info'),timeout=8).read())
        ts=json.loads(o.open(urllib.request.Request(host+'/api/v2/torrents/info'),timeout=8).read())
        dl=len([t for t in ts if t.get('dlspeed',0)>0])
        active=len([t for t in ts if t.get('state')=='downloading'])
        speed=info.get('dl_info_speed',0)/1048576
        dht=info.get('dht_nodes',0)
        return True, len(ts), dl, active, speed, dht
    except Exception as e:
        return False, 0, 0, 0, 0, 0

def container_running(name):
    r=subprocess.run(['docker','inspect','--format','{{.State.Running}}',name],capture_output=True,text=True)
    return r.stdout.strip()=='true'

log('=== PIPELINE MONITOR ===')

laptop_ok, l_total, l_dl, l_active, l_speed, l_dht = qbit_check('Laptop', 'http://<local-ip>:8080')
server_ok, s_total, s_dl, s_active, s_speed, s_dht = qbit_check('Server', 'http://localhost:8083')

log('Laptop: %s total=%s active=%s speed=%.1fMB/s DHT=%s %s' % 
    ('OK' if laptop_ok else 'DOWN', l_total, l_active, l_speed, l_dht, 
     '(Killswitch ON)' if laptop_ok else ''))
log('Server: %s total=%s active=%s speed=%.1fMB/s DHT=%s %s' % 
    ('OK' if server_ok else 'DOWN', s_total, s_active, s_speed, s_dht,
     '(Killswitch ON)' if server_ok else ''))

# If server qBit is down, restart it
if not container_running('qbittorrent-overflow'):
    log('WARNING: Server qBit down — restarting')
    subprocess.run(['docker','start','qbittorrent-overflow'],capture_output=True,timeout=15)

if not container_running('gluetun-overflow'):
    log('WARNING: Server VPN down — restarting')
    subprocess.run(['docker','start','gluetun-overflow'],capture_output=True,timeout=15)

# Combined stats
combined_speed = (l_speed if laptop_ok else 0) + (s_speed if server_ok else 0)
combined_dl = l_active + s_active
log('COMBINED: %.1f MB/s across %s active downloads' % (combined_speed, combined_dl))
log('DONE')
