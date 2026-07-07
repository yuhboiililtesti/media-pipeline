#!/usr/bin/env python3
"""PlexBot v2 — Polished Discord bot for Plex/Radarr/Sonarr/qBit pipeline."""

import urllib.request, urllib.parse, json, time, os, sys, re, xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ── CONFIG ───────────────────────────────────────────
TOKEN = "YOUR_DISCORD_TOKEN.APoJuHn3FMlmUVjbJ-aDYu93PWRGQ78_Cz5BcM"
CHAN_ID = "1481515715931537408"
PLEX_TOKEN = "YOUR_PLEX_TOKEN"
PLEX_URL = "http://localhost:32400"
RADARR_KEY = "YOUR_RADARR_API_KEY"
RADARR_URL = "http://localhost:7878"
SONARR_KEY = "YOUR_SONARR_API_KEY"
SONARR_URL = "http://localhost:8989"
QB_USER = "topaz"
QB_PASS = "YOUR_QBIT_PASSWORD"
COOLDOWN = {}  # Per-user cooldown tracking

HEADERS = {'Authorization': f'Bot {TOKEN}', 'User-Agent': 'PlexBot/2.0', 'Content-Type': 'application/json'}

# ── HELPERS ──────────────────────────────────────────
def now(): return datetime.now(timezone.utc)

def discord(path, method='GET', data=None, timeout=10):
    req = urllib.request.Request(f'https://discord.com/api/v10{path}',
        data=json.dumps(data).encode() if data else None, headers=HEADERS, method=method)
    r = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(r.read()) if r.status != 204 else None

def send(content=None, embed=None):
    data = {}
    if content: data['content'] = content
    if embed: data['embeds'] = [embed]
    discord(f'/channels/{CHAN_ID}/messages', method='POST', data=data)

def embed(title, desc='', fields=None, color=0xE5A00D, thumbnail=None):
    e = {'title': title, 'color': color, 'timestamp': now().isoformat()}
    if desc: e['description'] = str(desc)
    if fields: e['fields'] = fields
    if thumbnail: e['thumbnail'] = {'url': thumbnail}
    return e

def rate_limit(user_id, cmd, cooldown_sec=3):
    key = f"{user_id}:{cmd}"
    if key in COOLDOWN and time.time() - COOLDOWN[key] < cooldown_sec:
        return True
    COOLDOWN[key] = time.time()
    return False

def plex_get(path, timeout=8):
    url = f'{PLEX_URL}{path}'
    req = urllib.request.Request(url, headers={'X-Plex-Token': PLEX_TOKEN})
    r = urllib.request.urlopen(req, timeout=timeout)
    return ET.fromstring(r.read())

def radarr(path, method='GET', data=None, timeout=10):
    req = urllib.request.Request(f'{RADARR_URL}/api/v3{path}?apikey={RADARR_KEY}',
        data=json.dumps(data).encode() if data else None,
        headers={'Content-Type':'application/json'} if data else {}, method=method)
    r = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(r.read())

def sonarr(path, method='GET', data=None, timeout=10):
    req = urllib.request.Request(f'{SONARR_URL}/api/v3{path}?apikey={SONARR_KEY}',
        data=json.dumps(data).encode() if data else None,
        headers={'Content-Type':'application/json'} if data else {}, method=method)
    r = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(r.read())

def qbit_get(url, path, timeout=8):
    c = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(c)
    o.open(urllib.request.Request(f'{url}/api/v2/auth/login',
        data=urllib.parse.urlencode({'username':QB_USER,'password':QB_PASS}).encode()), timeout=timeout)
    return json.loads(o.open(urllib.request.Request(f'{url}{path}'), timeout=timeout).read()), o

def qbit_both():
    results = {}
    for label, url in [('Overflow','http://localhost:8083'),('Laptop','http://<local-ip>:8080')]:
        try:
            ts, o = qbit_get(url, '/api/v2/torrents/info')
            t, _ = qbit_get(url, '/api/v2/transfer/info') if False else (None, None)
            ts2, o2 = qbit_get(url, '/api/v2/torrents/info')
            t2, _ = qbit_get(url, '/api/v2/transfer/info') if False else (None, None)
            # Re-get transfer
            t = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/transfer/info'), timeout=5).read())
            dl = sum(1 for x in ts if x.get('dlspeed', 0) > 0)
            comp = sum(1 for x in ts if x.get('progress', 0) >= 1.0)
            speed = t.get('dl_info_speed', 0) / 1048576
            dht = t.get('dht_nodes', 0)
            results[label] = {'torrents': len(ts), 'dl': dl, 'comp': comp, 'speed': speed, 'dht': dht, 
                              'top': sorted([x for x in ts if x.get('dlspeed',0)>0], key=lambda x:-x.get('dlspeed',0))[:3]}
        except Exception as e:
            results[label] = {'error': str(e)[:60]}
    return results

def plex_sections():
    """Return dict of {type: {'key':..., 'title':..., 'count':...}}"""
    try:
        root = plex_get('/library/sections')
        sections = {}
        for d in root.findall('Directory'):
            key = d.get('key'); stype = d.get('type','?'); title = d.get('title','?')
            try:
                r2 = plex_get(f'/library/sections/{key}/all')
                count = r2.get('size', '?')
            except: count = '?'
            sections[stype] = {'key': key, 'title': title, 'count': count}
        return sections
    except: return {}

def plex_recent(limit=10):
    try:
        root = plex_get(f'/library/recentlyAdded?X-Plex-Container-Start=0&X-Plex-Container-Size={limit}')
        items = []
        for v in list(root)[:limit]:
            title = v.get('title', '?')
            year = v.get('year', '')
            stype = v.get('type', '?')
            items.append(f"{title} ({year})" if year else title)
        return items
    except: return []

# ── COMMANDS ─────────────────────────────────────────
def cmd_plex(user, args):
    try:
        root = plex_get('/identity')
        name = root.get('friendlyName', 'Plex')
        send(content=f'🟢 **{name}** is online')
    except: send(content='🔴 Plex is unreachable')

def cmd_status(user, args):
    try:
        sections = plex_sections()
        movies = sections.get('movie', {}).get('count', '?')
        shows = sections.get('show', {}).get('count', '?')
        recent = plex_recent(5)
        desc = f"🎬 **Movies:** {movies}\n📺 **TV Shows:** {shows}"
        if recent:
            desc += "\n\n**Recently Added:**\n" + '\n'.join(recent[:5])
        r = radarr('/movie')
        radarr_have = len([m for m in r if m.get('hasFile')])
        desc += f"\n\n📥 **Radarr:** {radarr_have}/{len(r)} have files"
        send(embed=embed('📊 Plex Status', desc))
    except Exception as e:
        send(content=f'❌ Status error: {e}')

def cmd_nowplaying(user, args):
    try:
        root = plex_get('/status/sessions')
        videos = list(root)
        if not videos:
            send(content='No active streams right now')
            return
        lines = []
        for v in videos:
            title = v.get('title', '?')
            user_el = v.find('User')
            player_el = v.find('Player')
            username = user_el.get('title', '?') if user_el is not None else '?'
            player = player_el.get('title', '?') if player_el is not None else '?'
            state = v.find('Player').get('state','playing') if v.find('Player') is not None else 'playing'
            emoji = '▶️' if state == 'playing' else '⏸️'
            lines.append(f"{emoji} **{title}** — {username} on {player}")
        send(embed=embed(f'Now Playing ({len(videos)})', '\n'.join(lines), color=0x00FF00))
    except Exception as e:
        send(content=f'❌ Session error: {e}')

def cmd_recent(user, args):
    items = plex_recent(10)
    if items:
        send(embed=embed('🆕 Recently Added', '\n'.join(items)))
    else:
        send(content='No recent items found')

def cmd_media(user, args):
    try:
        root = plex_get('/library/sections')
        lines = []
        total = 0
        for d in root.findall('Directory'):
            key = d.get('key'); stype = d.get('type','?'); title = d.get('title','?')
            count = plex_count(key)
            emoji = '🎬' if 'movie' in stype.lower() else '📺'
            lines.append(f"{emoji} **{title}:** {count}")
            if count != '?':
                total += int(count)
        lines.append(f"\n**Total:** {total}")
        send(embed=embed('📚 Media Libraries', '\n'.join(lines)))
    except Exception as e:
        send(content=f'❌ {e}')

def cmd_libraries(user, args): cmd_media(user, args)

def cmd_search(user, args):
    query = ' '.join(args)
    if not query: send(content='Usage: `!search <title>`'); return
    try:
        root = plex_get(f'/search?query={urllib.parse.quote(query)}')
        results = []
        for v in list(root)[:8]:
            title = v.get('title','?'); year = v.get('year',''); stype = v.get('type','?')
            summary = (v.get('summary','') or '')[:120]
            results.append(f"**{title}** ({year}) [{stype}]\n{summary}")
        if results:
            send(embed=embed(f'🔍 Search: {query}', '\n\n'.join(results)))
        else:
            send(content=f'No results for "{query}"')
    except: send(content='Search failed')

def cmd_has(user, args): cmd_search(user, args)

def cmd_drives(user, args):
    try:
        import shutil
        lines = []
        for mp, label in [('/mnt/20TB','20TB Media'),('/mnt/8TB','8TB Media'),('/','System SSD')]:
            try:
                s = shutil.disk_usage(mp)
                pct = s.used/s.total
                free = s.free/(1024**3); total = s.total/(1024**3)
                bar = '█'*int(pct*10)+'░'*(10-int(pct*10))
                status = '🟢' if pct < 0.8 else ('🟡' if pct < 0.9 else '🔴')
                lines.append(f"{status} **{label}** [{bar}] {free:.0f}GB free / {total:.0f}GB ({pct*100:.0f}%)")
            except: pass
        send(embed=embed('💾 Drive Usage', '\n'.join(lines)))
    except: send(content='Drive check failed')

def cmd_system(user, args):
    try:
        import subprocess as sp
        r = sp.run(['uptime','-p'], capture_output=True, text=True, timeout=5)
        uptime = r.stdout.strip()
        r = sp.run(['free','-h'], capture_output=True, text=True, timeout=5)
        mem = [l for l in r.stdout.split('\n') if 'Mem:' in l]
        mem_str = mem[0] if mem else '?'
        r = sp.run(['cat','/proc/loadavg'], capture_output=True, text=True, timeout=5)
        load = r.stdout.strip().split()[:3]
        lines = [
            f"**Uptime:** {uptime}",
            f"**Load:** {' '.join(load)}",
            f"**Memory:** {mem_str}",
        ]
        send(embed=embed('🖥️ System', '\n'.join(lines)))
    except: send(content='System check failed')

def cmd_health(user, args):
    try:
        import subprocess as sp, shutil
        r = sp.run(['docker','ps','--format','{{.Names}}'], capture_output=True, text=True, timeout=5)
        containers = len([l for l in r.stdout.strip().split('\n') if l])
        r = sp.run(['systemctl','is-active','auto-import.timer','plex-discord.timer'], capture_output=True, text=True, timeout=5)
        timers = r.stdout.strip().split()
        
        s = shutil.disk_usage('/mnt/20TB')
        disk_pct = (s.used/s.total)*100
        
        lines = [
            f"🐳 **Docker:** {containers} containers",
            f"⏱️ **Auto-import:** {'✅' if timers and timers[0]=='active' else '❌'}",
            f"🔔 **Plex Discord:** {'✅' if len(timers)>1 and timers[1]=='active' else '❌'}",
            f"💾 **20TB:** {disk_pct:.0f}% used",
            f"🏓 **Ping Bot:** {'✅' if containers > 10 else '⚠️'}",
        ]
        color = 0x00FF00 if all(['✅' in l for l in lines]) else 0xFFA500
        send(embed=embed('🩺 Health Check', '\n'.join(lines), color=color))
    except Exception as e:
        send(content=f'❌ Health: {e}')

def cmd_downloads(user, args):
    try:
        results = qbit_both()
        lines = []
        for label, data in results.items():
            if 'error' in data:
                lines.append(f"**{label}:** ❌ {data['error']}")
                continue
            lines.append(f"**{label}:** {data['torrents']} torrents • {data['dl']} DL @ {data['speed']:.1f}MB/s • DHT={data['dht']}")
            for t in data['top']:
                prog = int(t.get('progress',0)*100)
                spd = t.get('dlspeed',0)/1048576
                seeds = t.get('num_seeds',0)
                lines.append(f"  `[{prog}%]` {spd:.1f}MB/s 🌱{seeds} {t['name'][:45]}")
            if data['comp']:
                lines.append(f"  ✅ {data['comp']} completed (auto-importing)")
        send(embed=embed('📥 Downloads', '\n'.join(lines)))
    except Exception as e:
        send(content=f'❌ Downloads: {e}')

def search_plex(query):
    """Search Plex library. Returns list of {title, year, type} or []."""
    try:
        import urllib.parse as up
        root = plex_get(f'/search?query={up.quote(query)}')
        items = []
        for v in list(root)[:10]:
            items.append({'title': v.get('title','?'), 'year': v.get('year',''), 'type': v.get('type','?')})
        return items
    except: return []

def get_plex_movies(query):
    """Return list of Plex movies matching query."""
    try:
        results = search_plex(query)
        return [r for r in results if r['type'] == 'movie']
    except: return []

def get_radarr_movie(query, all_movies=None):
    """Find existing Radarr movie by title. Returns (movie, match_type) or (None, None)."""
    if all_movies is None:
        all_movies = radarr('/movie')
    q = query.lower().strip()
    # Exact match first
    for m in all_movies:
        if m.get('title','').lower().strip() == q:
            return m, 'exact'
    # Contains match
    for m in all_movies:
        if q in m.get('title','').lower():
            return m, 'contains'
    return None, None

def cmd_addmovie(user, args):
    query = ' '.join(args)
    if not query: send(content='Usage: `!addmovie <title>`'); return
    try:
        # 1. Check Radarr library (faster + more precise)
        all_movies = radarr('/movie')
        existing, match_type = get_radarr_movie(query, all_movies)
        if existing:
            if existing.get('hasFile'):
                send(content=f'📺 Already on **Plex**: {existing["title"]} ({existing.get("year","?")})')
            elif existing.get('monitored'):
                send(content=f'⏳ Already **requested**: {existing["title"]} ({existing.get("year","?")}) — downloading')
            else:
                send(content=f'📋 Already in **Radarr**: {existing["title"]} ({existing.get("year","?")}) — unmonitored')
            return
        
        # 2. Check Plex for exact title match
        plex_movies = get_plex_movies(query)
        exact_match = None
        for m in plex_movies:
            if query.lower().strip() == m['title'].lower().strip():
                exact_match = m
                break
        if exact_match:
            send(content=f'📺 Already on **Plex**: {exact_match["title"]} ({exact_match["year"]})')
            return
        
        # 3. If Plex has close matches but not exact, show them
        if plex_movies and not exact_match:
            close = [f'{m["title"]} ({m["year"]})' for m in plex_movies[:3]]
            send(content=f'🔍 Found similar on Plex: {", ".join(close)}\nAdd anyway with `!addmovie {query}` (already searching)')
        
        # 4. Look up on TMDB via Radarr and add
        results = radarr(f'/movie/lookup?term={urllib.parse.quote(query)}')
        if not results: send(content=f'🔍 No results for "{query}"'); return
        m = results[0]
        
        # Double-check not already in library by TMDB ID
        existing = [x for x in all_movies if x.get('tmdbId') == m.get('tmdbId')]
        if existing:
            ex = existing[0]
            if ex.get('hasFile'):
                send(content=f'📺 Already on **Plex**: {ex["title"]} ({ex.get("year","?")})')
            else:
                send(content=f'⏳ Already **requested**: {ex["title"]} ({ex.get("year","?")})')
            return
        
        data = {'title':m['title'],'qualityProfileId':6,'titleSlug':m['titleSlug'],'tmdbId':m['tmdbId'],
                'rootFolderPath':'/mnt/20TB/Movies 1','monitored':True,'addOptions':{'searchForMovie':True}}
        radarr('/movie', method='POST', data=data)
        send(content=f'✅ Added **{m["title"]}** ({m.get("year","?")}) — searching now')
    except Exception as e:
        send(content=f'❌ {e}')

def cmd_addtv(user, args):
    query = ' '.join(args)
    if not query: send(content='Usage: `!addtv <title>`'); return
    try:
        # 1. Check Sonarr library (faster + more precise)
        all_shows = sonarr('/series')
        q = query.lower().strip()
        existing = None
        for s in all_shows:
            if s.get('title','').lower().strip() == q:
                existing = s; break
        if not existing:
            for s in all_shows:
                if q in s.get('title','').lower():
                    existing = s; break
        
        if existing:
            stats = existing.get('statistics', {})
            ep_have = stats.get('episodeFileCount', 0)
            ep_total = stats.get('episodeCount', 0)
            if ep_have > 0:
                send(content=f'📺 Already on **Plex**: {existing["title"]} ({ep_have}/{ep_total} episodes)')
            elif existing.get('monitored'):
                send(content=f'⏳ Already **requested**: {existing["title"]} — waiting for episodes')
            else:
                send(content=f'📋 Already in **Sonarr**: {existing["title"]} — unmonitored')
            return
        
        # 2. Check Plex for exact match
        plex_results = search_plex(query)
        shows = [r for r in plex_results if r['type'] == 'show']
        for s in shows:
            if query.lower().strip() == s['title'].lower().strip():
                send(content=f'📺 Already on **Plex**: {s["title"]} ({s["year"]})')
                return
        
        # 3. Look up and add
        results = sonarr(f'/series/lookup?term={urllib.parse.quote(query)}')
        if not results: send(content=f'🔍 No results for "{query}"'); return
        s = results[0]
        
        # Double-check
        existing = [x for x in all_shows if x.get('tvdbId') == s.get('tvdbId')]
        if existing:
            ex = existing[0]
            stats = ex.get('statistics', {})
            if stats.get('episodeFileCount', 0) > 0:
                send(content=f'📺 Already on **Plex**: {ex["title"]}')
            else:
                send(content=f'⏳ Already **requested**: {ex["title"]}')
            return
        
        data = {'title':s['title'],'qualityProfileId':3,'titleSlug':s['titleSlug'],'tvdbId':s['tvdbId'],
                'rootFolderPath':'/mnt/20TB/TV Shows 1','monitored':True,'addOptions':{'searchForMissingEpisodes':True}}
        sonarr('/series', method='POST', data=data)
        send(content=f'✅ Added **{s["title"]}** ({s.get("year","?")}) — searching episodes')
    except Exception as e:
        send(content=f'❌ {e}')

def cmd_requests(user, args):
    try:
        r = radarr('/queue?pageSize=10')
        records = r.get('records', [])
        q = sonarr('/queue?pageSize=10')
        s_records = q.get('records', [])
        
        lines = []
        for rec in records[:5]:
            title = rec.get('title','?')[:55]
            status = rec.get('trackedDownloadStatus',rec.get('status','?'))
            dl = rec.get('downloadClient','?')
            lines.append(f"📽 `[{status}]` {title} — {dl}")
        for rec in s_records[:5]:
            title = rec.get('title','?')[:55]
            status = rec.get('trackedDownloadStatus',rec.get('status','?'))
            dl = rec.get('downloadClient','?')
            lines.append(f"📺 `[{status}]` {title} — {dl}")
        
        total = len(records) + len(s_records)
        if lines:
            send(embed=embed(f'📋 Active Downloads ({total})', '\n'.join(lines)))
        else:
            send(content='No active downloads in queue')
    except Exception as e:
        send(content=f'❌ {e}')

def cmd_gaming_on(user, args):
    try:
        for label, url in [('Overflow','http://localhost:8083'),('Laptop','http://<local-ip>:8080')]:
            c = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(c)
            o.open(urllib.request.Request(f'{url}/api/v2/auth/login',
                data=urllib.parse.urlencode({'username':QB_USER,'password':QB_PASS}).encode()), timeout=5)
            ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=5).read())
            if ts:
                hashes = '|'.join(t['hash'] for t in ts)
                o.open(urllib.request.Request(f'{url}/api/v2/torrents/pause',
                    data=urllib.parse.urlencode({'hashes':hashes}).encode(), method='POST'), timeout=5)
            prefs = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/app/preferences'), timeout=5).read())
            prefs['dl_limit']=0; prefs['up_limit']=0; prefs['max_active_downloads']=0; prefs['max_active_uploads']=0
            o.open(urllib.request.Request(f'{url}/api/v2/app/setPreferences',
                data=urllib.parse.urlencode({'json':json.dumps(prefs)}).encode(), method='POST'), timeout=5)
        send(content='🎮 **Gaming Mode ON** — all torrents paused, network freed')
    except Exception as e: send(content=f'❌ {e}')

def cmd_gaming_off(user, args):
    try:
        for label, url in [('Overflow','http://localhost:8083'),('Laptop','http://<local-ip>:8080')]:
            c = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(c)
            o.open(urllib.request.Request(f'{url}/api/v2/auth/login',
                data=urllib.parse.urlencode({'username':QB_USER,'password':QB_PASS}).encode()), timeout=5)
            prefs = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/app/preferences'), timeout=5).read())
            prefs['dl_limit']=0; prefs['up_limit']=0; prefs['max_active_downloads']=3; prefs['max_active_uploads']=2; prefs['max_active_torrents']=15; prefs['max_connec']=100
            o.open(urllib.request.Request(f'{url}/api/v2/app/setPreferences',
                data=urllib.parse.urlencode({'json':json.dumps(prefs)}).encode(), method='POST'), timeout=5)
            ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=5).read())
            if ts:
                hashes = '|'.join(t['hash'] for t in ts)
                o.open(urllib.request.Request(f'{url}/api/v2/torrents/resume',
                    data=urllib.parse.urlencode({'hashes':hashes}).encode(), method='POST'), timeout=5)
        send(content='⬇️ **Downloads Resumed** — limits restored, pipeline active')
    except Exception as e: send(content=f'❌ {e}')

def cmd_ping(user, args):
    host = args[0] if args else '1.1.1.1'
    try:
        import subprocess as sp
        r = sp.run(['ping','-c2','-W2',host], capture_output=True, text=True, timeout=6)
        send(content=f'```\n{r.stdout[:1900]}\n```')
    except: send(content=f'Ping to {host} failed')

def cmd_pipeline(user, args):
    modes = {'soft': (0,0,5,20,'🎮 SOFT — paused, network free'),
             'med': (3,2,15,100,'⚡ MED — balanced, ~3 DL per device'),
             'hard': (20,10,200,300,'🔥 HARD — max speed, ~20 DL per device')}
    if not args or args[0] not in modes:
        send(content='Usage: `!pipeline soft|med|hard`\n**soft** = pause all (gaming)\n**med** = balanced\n**hard** = max speed')
        return
    dl, ul, tor, conn, label = modes[args[0]]
    try:
        for l, url in [('Overflow','http://localhost:8083'),('Laptop','http://<local-ip>:8080')]:
            c = urllib.request.HTTPCookieProcessor(); o = urllib.request.build_opener(c)
            o.open(urllib.request.Request(f'{url}/api/v2/auth/login',
                data=urllib.parse.urlencode({'username':QB_USER,'password':QB_PASS}).encode()), timeout=5)
            prefs = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/app/preferences'), timeout=5).read())
            prefs['max_active_downloads']=dl; prefs['max_active_uploads']=ul
            prefs['max_active_torrents']=tor; prefs['max_connec']=conn
            prefs['dl_limit']=0; prefs['up_limit']=0
            o.open(urllib.request.Request(f'{url}/api/v2/app/setPreferences',
                data=urllib.parse.urlencode({'json':json.dumps(prefs)}).encode(), method='POST'), timeout=5)
            if dl == 0:
                ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=5).read())
                if ts:
                    hashes = '|'.join(t['hash'] for t in ts)
                    o.open(urllib.request.Request(f'{url}/api/v2/torrents/pause',
                        data=urllib.parse.urlencode({'hashes':hashes}).encode(), method='POST'), timeout=5)
            else:
                ts = json.loads(o.open(urllib.request.Request(f'{url}/api/v2/torrents/info'), timeout=5).read())
                paused = [t for t in ts if t.get('state')=='pausedDL']
                if paused:
                    hashes = '|'.join(t['hash'] for t in paused)
                    o.open(urllib.request.Request(f'{url}/api/v2/torrents/resume',
                        data=urllib.parse.urlencode({'hashes':hashes}).encode(), method='POST'), timeout=5)
        send(content=f'{label}\nOverflow: DL={dl} Tor={tor} Conn={conn}\nLaptop: DL={dl} Tor={tor} Conn={conn}')
    except Exception as e:
        send(content=f'❌ {e}')

def cmd_invite(user, args):
    email = ' '.join(args) if args else ''
    if not email or '@' not in email:
        send(content='Usage: `!invite user@email.com` — sends Plex invite')
        return
    try:
        # Plex invite API - use the shared users endpoint
        import urllib.parse as up
        server_id = 'd7ad8e2f2eaca81e3c4e4a887c46ae5a9e2b9270'
        
        # First check if already invited
        req = urllib.request.Request(
            f'https://plex.tv/api/servers/{server_id}/shared_servers?X-Plex-Token={PLEX_TOKEN}',
            headers={'Accept': 'application/json'})
        r = urllib.request.urlopen(req, timeout=10)
        shared = json.loads(r.read())
        
        # Check if email already shared
        for s in shared.get('MediaContainer', {}).get('SharedServer', []):
            username = s.get('@username', '') or s.get('username', '')
            user_email = s.get('@email', '') or s.get('email', '')
            if email.lower() == user_email.lower() or email.lower() == username.lower():
                send(content=f'📧 Already invited: {username or user_email}')
                return
        
        # Invite via Plex API
        invite_data = {
            'server_id': server_id,
            'shared_server': {
                'invited_email': email,
                'library_section_ids': [3, 5],  # Movies + TV
                'allow_sync': '0',
                'allow_camera_upload': '0',
                'allow_channels': '0',
                'filter_movies': '',
                'filter_television': '',
            }
        }
        
        req = urllib.request.Request(
            f'https://plex.tv/api/servers/{server_id}/shared_servers?X-Plex-Token={PLEX_TOKEN}',
            data=json.dumps(invite_data).encode(),
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            method='POST')
        r = urllib.request.urlopen(req, timeout=10)
        
        send(content=f'📧 Invite sent to **{email}** — they will receive an email from Plex\nLibraries shared: Movies + TV Shows')
    except Exception as e:
        err = str(e)
        if 'already' in err.lower() or 'exists' in err.lower():
            send(content=f'📧 **{email}** is already invited to Plex')
        else:
            send(content=f'❌ Invite failed: {err[:100]}\nTry manually: Plex → Settings → Users → Share')

def cmd_help(user, args):
    help_text = """**PlexBot Commands**
`!plex` — Plex health
`!status` — Full status + library
`!nowplaying` — Active streams
`!recent` — Recently added
`!media` / `!libraries` — Library counts
`!search <title>` — Search Plex
`!downloads` — qBit status (both)
`!drives` — Storage space
`!system` — CPU/Mem/Uptime
`!health` — Health summary
`!addmovie <title>` — Add to Radarr
`!addtv <title>` — Add to Sonarr
`!requests` — Active queue
`!gaming-on` / `!gaming-off` — Pause/Resume torrents
`!pipeline soft|med|hard|max` — Download power levels
`!invite <email>` — Send Plex library invite
`!ping [host]` — Ping test
`!help` — This message"""
    send(embed=embed('PlexBot Help', help_text))

COMMANDS = {
    '!plex': cmd_plex, '!status': cmd_status, '!nowplaying': cmd_nowplaying,
    '!recent': cmd_recent, '!media': cmd_media, '!libraries': cmd_libraries,
    '!search': cmd_search, '!has': cmd_search, '!drives': cmd_drives,
    '!system': cmd_system, '!health': cmd_health, '!downloads': cmd_downloads,
    '!ping': cmd_ping, '!addmovie': cmd_addmovie, '!addtv': cmd_addtv,
    '!requests': cmd_requests,     '!gaming-on': cmd_gaming_on, '!gaming-off': cmd_gaming_off,
    '!pipeline': cmd_pipeline, '!invite': cmd_invite,
    '!help': cmd_help,
}

# ── MAIN LOOP ────────────────────────────────────────
def main():
    global COOLDOWN
    last_msg_id = None
    
    # Seed last message
    try:
        msgs = discord(f'/channels/{CHAN_ID}/messages?limit=1')
        if msgs: last_msg_id = msgs[0]['id']
    except: pass
    
    print(f"PlexBot v2 started — {now().strftime('%H:%M:%S')}")
    
    while True:
        try:
            url = f'/channels/{CHAN_ID}/messages?limit=5'
            if last_msg_id: url += f'&after={last_msg_id}'
            msgs = discord(url)
            
            for msg in msgs:
                last_msg_id = msg['id']
                content = msg.get('content', '').strip()
                author = msg.get('author', {})
                
                if not content.startswith('!') or author.get('bot'):
                    continue
                
                user_id = author.get('id', '0')
                username = author.get('username', '?')
                cmd_name = content.split()[0].lower()
                
                # Rate limit
                if rate_limit(user_id, cmd_name, 3):
                    continue
                
                print(f"[{now().strftime('%H:%M:%S')}] {username}: {content[:60]}")
                
                handler = COMMANDS.get(cmd_name)
                if handler:
                    try:
                        args = content.split()[1:]
                        handler(username, args)
                    except Exception as e:
                        send(content=f'💥 Command error: `{e}`')
                elif cmd_name.startswith('!'):
                    send(content=f'Unknown: `{cmd_name}`. Try `!help`')
            
            time.sleep(3)
        except Exception as e:
            print(f"Loop: {e}")
            time.sleep(10)

if __name__ == '__main__':
    main()
