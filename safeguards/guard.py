#!/usr/bin/env python3
# safeguards/guard.py — Storage/health awareness + circuit breakers
# P0 checks run before discovery and imports

import json, os, subprocess, urllib.request

RULES_FILE = '/mnt/20TB/homelab/media/Pipeline/safeguards/rules.json'
QBIT_HOST = '<laptop-ip>:8080'
QBIT_USER = 'topaz'
QBIT_PASS = 'YOUR_QBIT_PASSWORD'

DEFAULT_RULES = {
    'content_filter_enabled': False,
    'never_download': [],
    'always_download': [],
    'max_per_day': {'movies': 10, 'shows': 5},
    'storage': {
        'reduce_at_pct': 85,
        'disable_8tb_at_pct': 98,
        'emergency_at_pct': 98,
        'check_drives': ['/mnt/20TB', '/mnt/8TB']
    },
    'health': {
        'vpn_required': False,
        'max_active_downloads': 18,
        'max_total_torrents': 450,
        'min_dht_nodes': 100
    }
}

def load_rules():
    if os.path.exists(RULES_FILE):
        try: return json.load(open(RULES_FILE))
        except: pass
    os.makedirs(os.path.dirname(RULES_FILE), exist_ok=True)
    json.dump(DEFAULT_RULES, open(RULES_FILE, 'w'), indent=2)
    return dict(DEFAULT_RULES)

def get_drive_pct(path):
    try:
        s = os.statvfs(path)
        return ((s.f_blocks - s.f_bavail) / s.f_blocks) * 100
    except:
        return 0

def check_8tb_overflow():
    """Check if 8TB is at/beyond disable threshold. Returns True if 8TB should NOT be used."""
    rules = load_rules()
    threshold = rules['storage'].get('disable_8tb_at_pct', 98)
    pct = get_drive_pct('/mnt/8TB')
    
    if pct >= threshold:
        return True, pct
    return False, pct

def protect_radarr_roots():
    """Remove 8TB root folders from Radarr when 8TB is full (>98%)"""
    overflow, pct = check_8tb_overflow()
    if not overflow:
        return False
    
    RADARR_KEY = 'YOUR_RADARR_API_KEY'
    SONARR_KEY = 'YOUR_SONARR_API_KEY'
    
    for name, port, key in [('Radarr', 7878, RADARR_KEY), ('Sonarr', 8989, SONARR_KEY)]:
        try:
            # Get root folders
            r = urllib.request.urlopen(f'http://localhost:{port}/api/v3/rootfolder?apikey={key}', timeout=10)
            roots = json.loads(r.read())
            
            for root in roots:
                path = root.get('path', '')
                if '/mnt/8TB' in path:
                    # Disable by setting free space to 0
                    root['freeSpace'] = 0
                    req = urllib.request.Request(
                        f'http://localhost:{port}/api/v3/rootfolder/{root["id"]}?apikey={key}',
                        data=json.dumps(root).encode(),
                        headers={'Content-Type': 'application/json'},
                        method='PUT')
                    urllib.request.urlopen(req, timeout=10)
                    print(f'  {name}: 8TB root folder disabled (freeSpace=0)')
        except Exception as e:
            print(f'  {name}: {e}')
    
    return True

def restore_radarr_roots():
    """Re-enable 8TB root folders when usage drops below threshold"""
    overflow, pct = check_8tb_overflow()
    if overflow:
        return False
    
    # Roots are auto-calculated by Radarr/Sonarr, just trigger refresh
    try:
        urllib.request.urlopen('http://localhost:7878/api/v3/rootfolder?apikey=YOUR_RADARR_API_KEY', timeout=10)
        urllib.request.urlopen('http://localhost:8989/api/v3/rootfolder?apikey=YOUR_SONARR_API_KEY', timeout=10)
        print('  Root folders refreshed')
    except:
        pass
    return True

def check_storage(rules):
    for drive in rules['storage']['check_drives']:
        pct = get_drive_pct(drive)
        if pct >= rules['storage']['emergency_at_pct']:
            return False, f'EMERGENCY: {drive} at {pct:.0f}%'
        if pct >= rules['storage']['reduce_at_pct']:
            return 'reduced', f'ELEVATED: {drive} at {pct:.0f}%'
    return True, 'OK'

def check_health(rules):
    if not rules.get('health', {}).get('vpn_required', False):
        return True, 'VPN check disabled'
    try:
        vpn = subprocess.run(['ssh', '-p', '2225', '-o', 'ConnectTimeout=5', 'laptop@<laptop-ip>',
            'sudo docker inspect gluetun --format {{.State.Health.Status}}'],
            capture_output=True, text=True, timeout=10)
        if 'healthy' not in vpn.stdout:
            return False, 'VPN unhealthy'
    except:
        return True, 'Cannot check VPN'
    return True, 'OK'

def is_protected_genre(genre_name, rules):
    if not rules.get('content_filter_enabled', False):
        return None
    return None
