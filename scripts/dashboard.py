#!/usr/bin/env python3
"""Pipeline Command Center v2 — Full control dashboard with drive management"""

import http.server, json, urllib.request, urllib.parse, os, subprocess, time, shlex
from datetime import datetime

PORT = 8090
TOKEN = 'YOUR_PLEX_TOKEN'
RADARR_KEY = 'YOUR_RADARR_API_KEY'
SONARR_KEY = 'YOUR_SONARR_API_KEY'
TMDB_KEY = 'YOUR_TMDB_API_KEY'

def qbit(path):
    try:
        cookie = urllib.request.HTTPCookieProcessor()
        o = urllib.request.build_opener(cookie)
        d = urllib.parse.urlencode({'username':'topaz','password':'YOUR_QBIT_PASSWORD'}).encode()
        o.open(urllib.request.Request('http://<local-ip>:8080/api/v2/auth/login',data=d),timeout=5)
        r = o.open(urllib.request.Request(f'http://<local-ip>:8080/api/v2{path}'),timeout=5)
        return json.loads(r.read())
    except: return {}

def arr(url):
    try: 
        with urllib.request.urlopen(url,timeout=5) as r: return json.loads(r.read())
    except: return {}

def run(cmd):
    try:
        r = subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=8)
        return r.stdout[:200] or 'ok'
    except: return 'timeout'

def get_state():
    s = {}
    
    # ─── QBIT ───
    info = qbit('/api/v2/transfer/info')
    torrents = qbit('/api/v2/torrents/info')
    ts = torrents if isinstance(torrents,list) else []
    s['qbit'] = {
        'dl': round(info.get('dl_info_speed',0)/1048576,1),
        'up': round(info.get('up_info_speed',0)/1048576,1),
        'dht': info.get('dht_nodes',0),
        'conn': info.get('connection_status','unknown'),
        'total': len(ts),
        'active': len([t for t in ts if t.get('dlspeed',0)>0]),
        'stalled': len([t for t in ts if t.get('state')=='stalledDL']),
        'paused': len([t for t in ts if t.get('state')=='pausedDL']),
        'completed': len([t for t in ts if t.get('progress',0)>=1]),
        'top': sorted([t for t in ts if t.get('dlspeed',0)>0],key=lambda x:-x['dlspeed'])[:6],
        'stalled_list': [t['name'][:50] for t in ts if t.get('state')=='stalledDL'][:5]
    }
    
    # ─── RADAAR ───
    movies = arr(f'http://localhost:7878/api/v3/movie?apikey={RADARR_KEY}')
    queue = arr(f'http://localhost:7878/api/v3/queue?apikey={RADARR_KEY}')
    history = arr(f'http://localhost:7878/api/v3/history?apikey={RADARR_KEY}&pageSize=8&sortKey=date&sortDirection=descending')
    if isinstance(movies,list):
        dl = sum(1 for m in movies if m.get('hasFile'))
        s['radarr'] = {
            'total':len(movies),'dl':dl,
            'missing':sum(1 for m in movies if m.get('monitored') and not m.get('hasFile')),
            'queue':len(queue.get('records',[])),
            'pct':round(dl/len(movies)*100) if movies else 0,
            'recent':[(r.get('eventType','?'),r.get('sourceTitle',r.get('movie',{}).get('title','?'))[:50]) for r in (history.get('records',[]) if history else [])[:5]]
        }
    else: s['radarr'] = {'total':0,'dl':0,'missing':0,'queue':0,'pct':0,'recent':[]}
    
    # ─── SONARR ───
    shows = arr(f'http://localhost:8989/api/v3/series?apikey={SONARR_KEY}')
    if isinstance(shows,list):
        eps = sum(s.get('statistics',{}).get('totalEpisodeCount',0) for s in shows)
        feps = sum(s.get('statistics',{}).get('episodeFileCount',0) for s in shows)
        s['sonarr'] = {
            'total':len(shows),'eps':eps,'feps':feps,'missing':eps-feps,
            'pct':round(feps/eps*100) if eps else 0,
            'top_missing':sorted([(s['title'],s.get('statistics',{}).get('totalEpisodeCount',0)-s.get('statistics',{}).get('episodeFileCount',0)) for s in shows if s.get('statistics',{}).get('totalEpisodeCount',0)-s.get('statistics',{}).get('episodeFileCount',0)>50],key=lambda x:-x[1])[:5]
        }
    else: s['sonarr'] = {'total':0,'eps':0,'feps':0,'missing':0,'pct':0,'top_missing':[]}
    
    # ─── ALL DRIVES ───
    s['drives'] = []
    for mp in ['/mnt/20TB','/mnt/8TB','/','/tmp','/home']:
        try:
            st = os.statvfs(mp)
            t = st.f_frsize*st.f_blocks/1e12
            f = st.f_frsize*st.f_bavail/1e12
            p = ((st.f_blocks-st.f_bavail)/st.f_blocks)*100
            # Check if 8TB is currently enabled in *arr
            active = True
            try:
                rr = arr(f'http://localhost:7878/api/v3/rootfolder?apikey={RADARR_KEY}')
                for root in (rr if isinstance(rr,list) else []):
                    if mp in root.get('path','') and root.get('freeSpace',1)==0: active = False
            except: pass
            s['drives'].append({'mount':mp,'name':os.path.basename(mp) or 'root','pct':round(p,1),'free':round(f,2),'total':round(t,2),'active':active})
        except: pass
    
    # ─── TIMERS ───
    r = subprocess.run('systemctl list-timers --no-pager',shell=True,capture_output=True,text=True)
    timer_names = ['torrent-doctor','tdarr-post-encode','balance-8tb','seed-finder','health-score',
                   'disk-space-guard','disk-watchdog','crash-watchdog','completed-import',
                   'discovery-engine','nightly-backup','complete-media','protect-8tb','pipeline-gc',
                   'pipeline-dashboard','cleanup-completed','vpn-watchdog','healer-check','healer-backup']
    s['timers'] = []
    for t in timer_names:
        s['timers'].append({'name':t,'active':t in r.stdout,'full':t in r.stdout})
    
    # ─── SERVICES ───
    services = ['plexmediaserver','docker','nfs-server']
    s['services'] = []
    for svc in services:
        r2 = subprocess.run(f'systemctl is-active {svc}',shell=True,capture_output=True,text=True)
        s['services'].append({'name':svc,'status':r2.stdout.strip()})
    
    # ─── HEALTH ───
    hp = '/mnt/20TB/homelab/media/Pipeline/state/HEALTH_SCORE.json'
    if os.path.exists(hp): s['health'] = json.load(open(hp))
    
    # ─── PLEX ───
    try:
        import xml.etree.ElementTree as ET
        r = urllib.request.urlopen(f'http://localhost:32400/library/sections?X-Plex-Token={TOKEN}',timeout=5)
        root = ET.fromstring(r.read())
        s['plex'] = {}
        for d in root.findall('Directory'):
            key = d.get('key'); title = d.get('title')
            try:
                r2 = urllib.request.urlopen(f'http://localhost:32400/library/sections/{key}/all?X-Plex-Token={TOKEN}',timeout=5)
                root2 = ET.fromstring(r2.read())
                items = len(root2.findall('.//Video')) + len(root2.findall('.//Directory'))
            except: items = 0
            s['plex'][title] = {'items':items,'type':d.get('type','?'),'key':key,'refreshing':d.get('refreshing','0')}
    except: s['plex'] = {}
    
    # ─── CANDIDATES ───
    cd = '/mnt/20TB/homelab/media/Pipeline/candidates'
    s['candidates'] = {}
    for q in ['auto_add','review_queue','quarantine','rejected']:
        qp = f'{cd}/{q}.txt'
        s['candidates'][q] = len(open(qp).readlines()) if os.path.exists(qp) else 0
    
    # ─── DOCKER (server) ───
    s['docker'] = []
    try:
        r = subprocess.run('docker ps --format "{{.Names}}|{{.Status}}"',shell=True,capture_output=True,text=True)
        for line in r.stdout.strip().split('\n'):
            if '|' in line:
                n,st = line.split('|',1)
                s['docker'].append({'name':n,'status':st[:30]})
    except: pass
    
    return s

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,f,*a): pass
    
    def _json(self,data):
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        p = self.path
        if p == '/': self._serve()
        elif p == '/api/state': self._json(get_state())
        elif p.startswith('/api/search'):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(p).query).get('q',[''])[0]
            results = []
            if q:
                try:
                    r = urllib.request.urlopen(f'https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={urllib.parse.quote(q)}',timeout=6)
                    for m in json.loads(r.read()).get('results',[])[:15]:
                        mt = m.get('media_type','movie')
                        if mt not in ('movie','tv'): continue
                        results.append({'id':m['id'],'title':m.get('title') or m.get('name','?'),'year':(m.get('release_date') or m.get('first_air_date') or '0000')[:4],'type':mt,'overview':(m.get('overview','') or '')[:120],'poster':f'https://image.tmdb.org/t/p/w92{m["poster_path"]}' if m.get('poster_path') else ''})
                except: pass
            self._json(results)
        elif p.startswith('/api/action'):
            a = urllib.parse.parse_qs(urllib.parse.urlparse(p).query).get('a',[''])[0]
            arg = urllib.parse.parse_qs(urllib.parse.urlparse(p).query).get('arg',[''])[0]
            result = 'ok'
            if a == 'discover': run('TMDB_KEY='+TMDB_KEY+' PYTHONPATH=/mnt/20TB/homelab/media/Pipeline python3 /mnt/20TB/homelab/media/Pipeline/discovery/engine.py daily &')
            elif a == 'complete': run('python3 /mnt/20TB/homelab/media/Pipeline/scripts/complete-media.py &')
            elif a == 'doctor': run('/mnt/20TB/homelab/media/Pipeline/scripts/torrent-doctor.sh &')
            elif a == 'balance': run('python3 /mnt/20TB/homelab/media/Pipeline/scripts/balance-8tb.sh &')
            elif a == 'backup': run('/mnt/20TB/homelab/media/Pipeline/scripts/nightly-backup.sh &')
            elif a == 'disable_drive':
                if '8TB' in arg: run('sudo systemctl stop protect-8tb.timer 2>/dev/null; sudo systemctl stop balance-8tb.timer 2>/dev/null')
                result = f'{arg} pipeline stopped'
            elif a == 'enable_drive':
                if '8TB' in arg: run('sudo systemctl start protect-8tb.timer 2>/dev/null; sudo systemctl start balance-8tb.timer 2>/dev/null')
                result = f'{arg} pipeline enabled'
            elif a == 'restart_service':
                run(f'sudo systemctl restart {arg} 2>/dev/null')
                result = f'{arg} restarting'
            elif a == 'stop_timer':
                run(f'sudo systemctl stop {arg}.timer 2>/dev/null')
                result = f'{arg} stopped'
            elif a == 'start_timer':
                run(f'sudo systemctl start {arg}.timer 2>/dev/null')
                result = f'{arg} started'
            elif a == 'refresh_plex':
                run(f'curl -s "http://localhost:32400/library/sections/{arg}/refresh?X-Plex-Token={TOKEN}" &')
                result = f'Plex section {arg} refreshing'
            self._json({'status':result})
        else: self.send_response(404); self.end_headers()
    
    def do_POST(self):
        length = int(self.headers.get('Content-Length',0))
        body = self.rfile.read(length).decode() if length else ''
        params = urllib.parse.parse_qs(body)
        tid = int(params.get('id',[0])[0])
        mt = params.get('type',['movie'])[0]
        if mt == 'movie':
            p = {'tmdbId':tid,'qualityProfileId':6,'monitored':True,'rootFolderPath':'/mnt/20TB/Movies 1','addOptions':{'searchForMovie':True}}
            try:
                r = urllib.request.urlopen(urllib.request.Request(f'http://localhost:7878/api/v3/movie?apikey={RADARR_KEY}',data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='POST'),timeout=10)
                self._json({'status':'added','id':json.loads(r.read()).get('id')})
            except Exception as e: self._json({'status':'error','msg':str(e)[:60]})
        else:
            try:
                r = urllib.request.urlopen(f'http://localhost:8989/api/v3/lookup?apikey={SONARR_KEY}&term=tmdb:{tid}',timeout=10)
                data = json.loads(r.read())
                if data:
                    s = data[0]
                    p = {'tvdbId':s['tvdbId'],'title':s['title'],'qualityProfileId':3,'monitored':True,'rootFolderPath':'/mnt/20TB/TV Shows 1','seasons':s.get('seasons',[]),'addOptions':{'searchForMissingEpisodes':True}}
                    r2 = urllib.request.urlopen(urllib.request.Request(f'http://localhost:8989/api/v3/series?apikey={SONARR_KEY}',data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='POST'),timeout=10)
                    self._json({'status':'added','id':json.loads(r2.read()).get('id')})
                else: self._json({'status':'error','msg':'Not found'})
            except Exception as e: self._json({'status':'error','msg':str(e)[:60]})
    
    def _serve(self):
        html = r'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pipeline Command Center v2</title>
<style>
:root{--bg:#090d13;--card:#0f1419;--border:#1a2030;--text:#b0b8c4;--dim:#4a5568;--green:#3fb950;--yellow:#d29922;--red:#f85149;--blue:#58a6ff;--orange:#ff8f40}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:"SF Mono","Cascadia Code",monospace;font-size:11px;line-height:1.5}
.layout{display:grid;grid-template-columns:280px 1fr;min-height:100vh}
.sidebar{background:var(--card);border-right:1px solid var(--border);padding:12px;overflow-y:auto}
.sidebar h2{color:var(--orange);font-size:11px;text-transform:uppercase;letter-spacing:2px;margin-bottom:12px}
.main{padding:14px;overflow-y:auto}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px}
.topbar .time{color:var(--dim)}
.btn{padding:5px 10px;background:var(--card);border:1px solid var(--border);color:var(--text);cursor:pointer;font-family:inherit;font-size:10px;border-radius:3px;white-space:nowrap;display:inline-flex;align-items:center;gap:4px}
.btn:hover{border-color:var(--orange);color:var(--orange)}
.btn.g{background:#0d2b0d;border-color:#1a4a1a;color:var(--green)}.btn.g:hover{border-color:var(--green)}
.btn.r{background:#2b0d0d;border-color:#4a1a1a;color:var(--red)}.btn.r:hover{border-color:var(--red)}
.btn.b{background:#0d1a2b;border-color:#1a2d4a;color:var(--blue)}.btn.b:hover{border-color:var(--blue)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:10px}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--border);border-radius:4px;padding:12px}
.card h3{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--dim);margin-bottom:8px;display:flex;align-items:center;gap:6px}
.card h3 .dot{width:6px;height:6px;border-radius:50%}.card h3 .dot.on{background:var(--green)}.card h3 .dot.off{background:var(--red)}
.row{display:flex;justify-content:space-between;padding:1px 0;font-size:10px}
.row .l{color:var(--dim)}.row .v{color:var(--text)}.row .g{color:var(--green)}.row .y{color:var(--yellow)}.row .r{color:var(--red)}
.bar{height:3px;background:var(--border);margin:3px 0 6px;border-radius:2px;overflow:hidden}
.bar div{height:100%;border-radius:2px;transition:width .6s}
.stream{font-size:9px;color:var(--dim);max-height:80px;overflow:hidden;margin-top:4px}
.stream div{padding:0.5px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.drive-row{display:flex;align-items:center;justify-content:space-between;padding:2px 0}
.drive-row .name{font-size:10px}
.drive-row select{background:var(--bg);border:1px solid var(--border);color:var(--text);font-family:inherit;font-size:9px;padding:2px 4px;border-radius:2px}
.searchbox{margin-bottom:6px}
.searchbox input{width:100%;padding:6px 10px;background:var(--bg);border:1px solid var(--border);color:var(--text);font-family:inherit;font-size:10px;border-radius:3px}
.searchbox input:focus{outline:none;border-color:var(--orange)}
#results .res{background:var(--bg);border:1px solid var(--border);padding:6px;cursor:pointer;display:flex;gap:6px;align-items:center;margin-bottom:4px;border-radius:3px;font-size:9px}
#results .res:hover{border-color:var(--orange)}
#results img{width:28px;height:42px;object-fit:cover;border-radius:2px;flex-shrink:0}
.toast{position:fixed;bottom:14px;right:14px;background:#0d2b0d;border:1px solid #1a4a1a;color:var(--green);padding:8px 14px;border-radius:4px;font-size:10px;z-index:999;display:none}
.collapsible{cursor:pointer}.collapsible:hover{color:var(--orange)}
</style></head><body>
<div class="layout">
<div class="sidebar">
<h2>◈ COMMAND CENTER</h2>
<div class="searchbox"><input id="sq" placeholder="Search & add media..." onkeyup="if(event.key==='Enter')doSearch()"></div>
<div id="results"></div>
<hr style="border-color:var(--border);margin:10px 0">
<div class="btn g" onclick="action('discover')" style="width:100%;margin-bottom:4px">▶ Run Discovery</div>
<div class="btn g" onclick="action('complete')" style="width:100%;margin-bottom:4px">◆ Complete Media</div>
<div class="btn" onclick="action('doctor')" style="width:100%;margin-bottom:4px">♺ Torrent Doctor</div>
<div class="btn" onclick="action('balance')" style="width:100%;margin-bottom:4px">⇄ Balance Disks</div>
<div class="btn" onclick="action('backup')" style="width:100%;margin-bottom:4px">⬆ Nightly Backup</div>
<div class="btn b" onclick="action('restart_service','plexmediaserver')" style="width:100%;margin-bottom:4px">↻ Restart Plex</div>
<hr style="border-color:var(--border);margin:10px 0">
<div id="drivelist"></div>
</div>
<div class="main">
<div class="topbar"><div class="time" id="clock"></div><div id="service-dots"></div></div>
<div class="grid2" id="dash"></div>
</div></div>
<div class="toast" id="toast"></div>
<script>
const POLL=4000;
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.style.display='block';setTimeout(()=>t.style.display='none',2000)}

async function fs(){const r=await fetch('/api/state');return r.json()}

async function render(){
  const d=await fs();
  document.getElementById('clock').textContent=new Date().toLocaleString();
  
  // Service dots
  let svcDots='';
  if(d.services) d.services.forEach(s=>{
    const ok=s.status==='active'; svcDots+=`<span style="color:${ok?'var(--green)':'var(--red)'};margin-right:8px;font-size:10px">${ok?'●':'○'} ${s.name}</span>`;
  });
  document.getElementById('service-dots').innerHTML=svcDots;
  
  // Drive list in sidebar
  let dl='';
  if(d.drives) d.drives.forEach(dr=>{
    const c=dr.pct>90?'r':dr.pct>80?'y':'g';
    dl+=`<div style="margin-bottom:6px"><div class="row"><span class="l">${dr.mount}</span><span class="${c}">${dr.pct}%</span></div>
    <div class="bar"><div style="background:${dr.pct>90?'var(--red)':dr.pct>80?'var(--yellow)':'var(--green)'};width:${dr.pct}%"></div></div>
    <div class="row"><span class="l">${dr.free}TB free / ${dr.total}TB</span><span class="l">${dr.active?'▶ active':'■ stopped'}</span></div>
    <select onchange="driveAction(this.value,'${dr.mount}')" style="width:100%;margin-top:2px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:3px;font-family:inherit;font-size:9px">
      <option value="">Drive actions...</option>
      <option value="enable">Enable in pipeline</option>
      <option value="disable">Stop using this drive</option>
    </select></div>`;
  });
  document.getElementById('drivelist').innerHTML=dl;
  
  let h='';
  
  // qBit
  if(d.qbit){ const q=d.qbit;
    h+=`<div class="card"><h3><span class="dot ${q.conn=='connected'?'on':'off'}"></span>qBittorrent</h3>
      <div class="row"><span class="l">Download</span><span class="g">${q.dl} MB/s</span></div>
      <div class="row"><span class="l">Upload</span><span class="v">${q.up} MB/s</span></div>
      <div class="row"><span class="l">DHT Nodes</span><span class="${q.dht>300?'g':'y'}">${q.dht}</span></div>
      <div class="row"><span class="l">Active / Total / Stalled</span><span class="g">${q.active}</span><span class="v"> / ${q.total}</span><span class="${q.stalled>10?'r':'y'}"> / ${q.stalled}</span></div>
      <div class="bar"><div style="background:var(--green);width:${q.total>0?q.active/q.total*100:0}%"></div></div>`;
    if(q.top) q.top.forEach(t=>{h+=`<div class="stream"><div>${(t.dlspeed/1048576).toFixed(1)}MB/s ${t.name.substring(0,50)}</div></div>`});
    if(q.stalled_list) q.stalled_list.forEach(t=>{h+=`<div class="stream"><div style="color:var(--yellow)">⚠ ${t}</div></div>`});
    h+=`</div>`;
  }
  
  // Radarr
  if(d.radarr){ h+=`<div class="card"><h3>🎬 Radarr — ${d.radarr.total} movies</h3>
    <div class="row"><span class="l">Downloaded</span><span class="g">${d.radarr.dl}</span><span class="v"> / ${d.radarr.total} (${d.radarr.pct}%)</span></div>
    <div class="row"><span class="l">Missing</span><span class="y">${d.radarr.missing}</span><span class="l"> | Queue: ${d.radarr.queue}</span></div>
    <div class="bar"><div style="background:var(--green);width:${d.radarr.pct}%"></div></div>`;
    if(d.radarr.recent) d.radarr.recent.forEach(([et,t])=>{h+=`<div class="stream"><div>[${et}] ${t}</div></div>`});
    h+=`</div>`;}
  
  // Sonarr
  if(d.sonarr){ h+=`<div class="card"><h3>📺 Sonarr — ${d.sonarr.total} shows</h3>
    <div class="row"><span class="l">Episodes</span><span class="g">${d.sonarr.feps}</span><span class="v"> / ${d.sonarr.eps} (${d.sonarr.pct}%)</span></div>
    <div class="row"><span class="l">Missing</span><span class="y">${d.sonarr.missing}</span></div>
    <div class="bar"><div style="background:var(--green);width:${d.sonarr.pct}%"></div></div>`;
    if(d.sonarr.top_missing) d.sonarr.top_missing.forEach(([n,c])=>{h+=`<div class="stream"><div>${n}: ${c} missing</div></div>`});
    h+=`</div>`;}
  
  // Plex
  if(d.plex){ h+=`<div class="card"><h3>▶ Plex</h3>`;
    for(const [lib,info] of Object.entries(d.plex)){
      h+=`<div class="row"><span class="l">${lib} (${info.type})</span><span class="v">${info.items} items</span><span class="l" style="cursor:pointer" onclick="action('refresh_plex','${info.key}')">↻</span></div>`;}
    h+=`</div>`;}
  
  // Docker
  if(d.docker){ h+=`<div class="card collapsible" onclick="this.querySelector('.content').style.display=this.querySelector('.content').style.display=='none'?'block':'none'"><h3>🐳 Docker Containers</h3><div class="content" style="display:none">`;
    d.docker.forEach(c=>{h+=`<div class="row"><span class="l">${c.name}</span><span class="v">${c.status}</span></div>`});
    h+=`</div></div>`;}
  
  // Timers
  const active = d.timers?d.timers.filter(t=>t.active).length:0;
  const total = d.timers?d.timers.length:0;
  h+=`<div class="card collapsible" onclick="this.querySelector('.content').style.display=this.querySelector('.content').style.display=='none'?'block':'none'"><h3>⏱ Timers — ${active}/${total} active</h3><div class="content" style="display:none">`;
  if(d.timers) d.timers.forEach(t=>{
    h+=`<div class="row"><span class="l">${t.name}</span><span class="${t.active?'g':'r'}">${t.active?'●':'○'}</span></div>`});
  h+=`</div></div>`;
  
  // Health
  if(d.health){ const s=d.health; const c=s.overall>70?'var(--green)':s.overall>40?'var(--yellow)':'var(--red)';
    h+=`<div class="card"><h3>❤ Health — ${s.overall}/100</h3>
      <div class="bar"><div style="background:${c};width:${s.overall}%"></div></div>
      <div class="row"><span class="l">Storage</span><span class="${s.storage>50?'g':'y'}">${s.storage}</span></div>
      <div class="row"><span class="l">Downloads</span><span class="${s.downloads>50?'g':'y'}">${s.downloads}</span></div>
      <div class="row"><span class="l">Network</span><span class="g">${s.network}</span></div>
      <div class="row"><span class="l">Plex</span><span class="g">${s.plex}</span></div></div>`;}
  
  // Candidates
  if(d.candidates){ h+=`<div class="card"><h3>📋 Discovery Queue</h3>
    <div class="row"><span class="l">Auto-Add</span><span class="g">${d.candidates.auto_add||0}</span></div>
    <div class="row"><span class="l">Review</span><span class="y">${d.candidates.review_queue||0}</span></div>
    <div class="row"><span class="l">Quarantine</span><span class="y">${d.candidates.quarantine||0}</span></div>
    <div class="row"><span class="l">Rejected</span><span class="r">${d.candidates.rejected||0}</span></div></div>`;}
  
  document.getElementById('dash').innerHTML=h;
}

let searchTimer;
document.getElementById('sq').addEventListener('input',function(){
  clearTimeout(searchTimer);
  const q=this.value; if(q.length<2){document.getElementById('results').innerHTML='';return}
  searchTimer=setTimeout(async()=>{const r=await fetch('/api/search?q='+encodeURIComponent(q));const d=await r.json();
    let h=''; d.forEach(i=>{h+=`<div class="res" onclick="add(${i.id},'${i.type}','${i.title.replace(/'/g,"\\'")}')">
      ${i.poster?`<img src="${i.poster}">`:'<div style="width:28px;height:42px;background:var(--border)"></div>'}
      <div><b>${i.title}</b><br>${i.year} · ${i.type}${i.overview?`<br><span style="color:var(--dim)">${i.overview.substring(0,80)}</span>`:''}</div></div>`});
    document.getElementById('results').innerHTML=h||'<div style="color:var(--dim);font-size:10px">No results</div>'},300)});

async function add(id,type,title){
  const r=await fetch('/api/add',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:`id=${id}&type=${type}`});
  const d=await r.json(); toast(d.status=='added'?`✓ ${title}`:'✗ '+d.msg);
  document.getElementById('results').innerHTML=''; document.getElementById('sq').value=''; render()}

async function action(a,arg=''){
  const r=await fetch(`/api/action?a=${a}&arg=${encodeURIComponent(arg)}`); const d=await r.json();
  toast(d.status||'ok'); setTimeout(render,1500)}

function driveAction(a,mount){if(a)action(a,mount.replace('/mnt/',''))}
async function doSearch(){const q=document.getElementById('sq').value;if(!q)return;
  const r=await fetch('/api/search?q='+encodeURIComponent(q));const d=await r.json();
  let h=''; d.forEach(i=>{h+=`<div class="res" onclick="add(${i.id},'${i.type}','${i.title.replace(/'/g,"\\'")}')">${i.poster?`<img src="${i.poster}">`:''}<div>${i.title}<br>${i.year} · ${i.type}</div></div>`});
  document.getElementById('results').innerHTML=h||'<div>No results</div>'})

render();setInterval(render,POLL);
</script></body></html>'''
        self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers()
        self.wfile.write(html.encode())

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0',8090), Handler)
    server.serve_forever()
