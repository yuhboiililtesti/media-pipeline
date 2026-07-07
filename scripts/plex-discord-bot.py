#!/usr/bin/env python3
"""Plex Discord Bot — sends recently added media announcements to Discord.
   Polls Plex for new additions, formats embeds, sends via webhook.
   Tracks announced items to avoid duplicates.

   Config: /mnt/20TB/homelab/media/Pipeline/plex-discord.conf
   State:  /mnt/20TB/homelab/media/Pipeline/state/plex-discord-state.json
"""

import urllib.request, urllib.parse, json, os, time, sys
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────
CONFIG_FILE = '/mnt/20TB/homelab/media/Pipeline/plex-discord.conf'
STATE_FILE  = '/mnt/20TB/homelab/media/Pipeline/state/plex-discord-state.json'
LOG_FILE    = '/mnt/20TB/homelab/media/Pipeline/logs/plex-discord.log'

def load_config():
    """Load config from file, use defaults if missing."""
    cfg = {
        'plex_url': 'http://localhost:32400',
        'plex_token': 'YOUR_PLEX_TOKEN',
        'discord_webhook': '',
        'check_interval_minutes': 10,
        'max_per_run': 5,
        'announce_movies': True,
        'announce_shows': True,
        'announce_episodes': False,
        'movie_emoji': ':film_frames:',
        'show_emoji': ':tv:',
        'episode_emoji': ':clapper:',
        'message_color': 0xE5A00D,  # Plex orange
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip()
                        if k in cfg:
                            if v.lower() in ('true', 'false'):
                                cfg[k] = v.lower() == 'true'
                            elif v.lower() in ('yes', 'no'):
                                cfg[k] = v.lower() == 'yes'
                            elif v.startswith('0x'):
                                cfg[k] = int(v, 16)
                            elif v.isdigit():
                                cfg[k] = int(v)
                            else:
                                cfg[k] = v
    return cfg

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{timestamp}] {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass

def plex_get(cfg, path, timeout=10):
    """Make authenticated Plex API request."""
    url = f"{cfg['plex_url']}{path}"
    headers = {
        'X-Plex-Token': cfg['plex_token'],
        'Accept': 'application/json',
    }
    req = urllib.request.Request(url, headers=headers)
    r = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(r.read())

def load_state():
    """Load previously announced items."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {'announced': {}, 'last_check': 0}

def save_state(state):
    """Save announced items state."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def send_discord(cfg, embeds):
    """Send embeds to Discord webhook."""
    if not cfg['discord_webhook']:
        log('No Discord webhook configured — skipping')
        return False

    data = json.dumps({'embeds': embeds}).encode()
    req = urllib.request.Request(cfg['discord_webhook'],
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=10)
        if r.getcode() in (200, 204):
            return True
        log(f'Discord webhook returned {r.getcode()}')
        return False
    except Exception as e:
        log(f'Discord webhook failed: {e}')
        return False

def get_recently_added(cfg, since_timestamp):
    """Get items added since last check."""
    items = []

    if cfg['announce_movies']:
        try:
            data = plex_get(cfg, '/library/sections/3/recentlyAdded?X-Plex-Container-Start=0&X-Plex-Container-Size=20')
            for item in data.get('MediaContainer', {}).get('Metadata', []):
                added = item.get('addedAt', 0)
                if added > since_timestamp:
                    items.append({
                        'id': f"movie-{item.get('ratingKey')}",
                        'type': 'movie',
                        'title': item.get('title', 'Unknown'),
                        'year': item.get('year', '?'),
                        'summary': (item.get('summary', '') or '')[:256],
                        'duration': item.get('duration', 0) // 60000,
                        'thumb': f"{cfg['plex_url']}{item.get('thumb', '')}?X-Plex-Token={cfg['plex_token']}" if item.get('thumb') else None,
                        'added': added,
                    })
        except Exception as e:
            log(f'Movie fetch error: {e}')

    if cfg['announce_shows']:
        try:
            data = plex_get(cfg, '/library/sections/5/recentlyAdded?X-Plex-Container-Start=0&X-Plex-Container-Size=20')
            for item in data.get('MediaContainer', {}).get('Metadata', []):
                added = item.get('addedAt', 0)
                if item.get('type') == 'show' and added > since_timestamp:
                    items.append({
                        'id': f"show-{item.get('ratingKey')}",
                        'type': 'show',
                        'title': item.get('title', 'Unknown'),
                        'year': item.get('year', '?'),
                        'summary': (item.get('summary', '') or '')[:256],
                        'seasons': f"{item.get('childCount', item.get('leafCount', '?'))} episodes",
                        'thumb': f"{cfg['plex_url']}{item.get('thumb', '')}?X-Plex-Token={cfg['plex_token']}" if item.get('thumb') else None,
                        'added': added,
                    })
        except Exception as e:
            log(f'Show fetch error: {e}')

    return sorted(items, key=lambda x: x['added'], reverse=True)

def format_embed(cfg, item):
    """Create Discord embed for a single item."""
    if item['type'] == 'movie':
        emoji = cfg['movie_emoji']
        title = f"{emoji} {item['title']} ({item['year']})"
        desc = item.get('summary', '') or f"Duration: {item.get('duration', '?')} min"
        footer = f"Movie | Added {datetime.fromtimestamp(item['added']).strftime('%m/%d %H:%M')}"
    elif item['type'] == 'show':
        emoji = cfg['show_emoji']
        title = f"{emoji} {item['title']} ({item['year']})"
        desc = item.get('summary', '') or f"{item.get('seasons', '?')}"
        footer = f"TV Show | Added {datetime.fromtimestamp(item['added']).strftime('%m/%d %H:%M')}"
    else:
        emoji = cfg['episode_emoji']
        title = f"{emoji} {item.get('show_title', '?')} - {item['title']}"
        desc = f"Season {item.get('season', '?')} Episode {item.get('episode', '?')}"
        footer = f"Episode | Added {datetime.fromtimestamp(item['added']).strftime('%m/%d %H:%M')}"

    embed = {
        'title': title,
        'description': desc,
        'color': cfg['message_color'],
        'footer': {'text': footer},
        'timestamp': datetime.fromtimestamp(item['added']).isoformat(),
    }

    if item.get('thumb'):
        embed['thumbnail'] = {'url': item['thumb']}

    return embed

def main():
    cfg = load_config()

    if not cfg['discord_webhook']:
        log('ERROR: No discord_webhook configured in ' + CONFIG_FILE)
        log('Set DISCORD_WEBHOOK=https://discord.com/api/webhooks/... and restart')
        sys.exit(1)

    state = load_state()
    since = state.get('last_check', time.time() - 3600)  # default: 1 hour
    now = time.time()

    items = get_recently_added(cfg, since)
    new_items = [i for i in items if i['id'] not in state['announced']]
    new_items = new_items[:cfg['max_per_run']]

    if not new_items:
        log(f'No new content since {datetime.fromtimestamp(since).strftime("%H:%M")} — {len(items)} total recent')
        state['last_check'] = now
        save_state(state)
        return

    embeds = []
    for item in new_items:
        embed = format_embed(cfg, item)
        embeds.append(embed)
        state['announced'][item['id']] = now
        log(f"New: {item['type']} — {item['title']}")

    if embeds:
        if send_discord(cfg, embeds):
            log(f'Sent {len(embeds)} announcement{"s" if len(embeds)>1 else ""} to Discord')
            state['last_check'] = now
            save_state(state)
        else:
            log('Failed to send Discord messages')

    # Prune old announcements (keep last 7 days)
    cutoff = now - (7 * 86400)
    state['announced'] = {k: v for k, v in state['announced'].items() if v > cutoff}

if __name__ == '__main__':
    main()
