import os, re, shutil, sys

MOVIE_DIRS = ['/mnt/20TB/Movies 1', '/mnt/8TB/Movies 2']
TV_DIRS = ['/mnt/20TB/TV Shows 1', '/mnt/8TB/TV Shows 2']

# Strong TV patterns (S##E##, S##., Season #, EP##)
TV_STRONG = [
    r'[Ss]\d{2}[Ee]\d{2}',   # S01E01
    r'[Ss]\d{2}\.',           # S01.
    r'Season\s*\d+',          # Season 1
    r'EP\d{2}',               # EP01  
]

def is_tv_show(name):
    for pat in TV_STRONG:
        if re.search(pat, name): return True
    return False

def is_movie_extra(name):
    # Skip: James Bond extras, movie bonus features
    extras = ['Inside ', 'Behind ', 'Making of', 'Featurette', 'Commentary',
              'NCOP', 'NCED', 'PV', 'Preview', 'Notice CM', 'Short Anime',
              'Bonus Track', 'Special Event']
    return any(e.lower() in name.lower() for e in extras)

moved = 0
for mdir in MOVIE_DIRS:
    if not os.path.isdir(mdir): continue
    for item in os.listdir(mdir):
        item_path = os.path.join(mdir, item)
        if not os.path.isdir(item_path): continue
        
        # Skip movie extras/bonus content
        if is_movie_extra(item):
            print(f'  SKIP (extra): {item}')
            continue
            
        # Skip Open Season movies  
        if 'open season' in item.lower():
            print(f'  SKIP (movie): {item}')
            continue

        if is_tv_show(item):
            # Find TV dir on same disk
            for tvdir in TV_DIRS:
                if os.path.isdir(tvdir) and tvdir[:10] == mdir[:10]:
                    dst = os.path.join(tvdir, item)
                    print(f'  MOVE: {item} -> TV Shows')
                    try:
                        shutil.move(item_path, dst)
                        os.chown(dst, 1000, 1000)
                        moved += 1
                    except Exception as e:
                        print(f'  FAIL: {e}')
                    break

print(f'Done. Moved {moved} items.')

if moved > 0:
    import subprocess
    subprocess.run(['curl','-s','-X','POST',
        'http://127.0.0.1:8989/api/v3/command?apikey=SONARR_API_KEY',
        '-H','Content-Type: application/json',
        '-d','{"name":"RescanSeries"}'], timeout=10)
    print('Sonarr rescan triggered')
