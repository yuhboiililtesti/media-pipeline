# media-pipeline

my homelab media pipeline that runs itself. built it because i got tired of manually finding movies, waiting for downloads, importing to plex, cleaning up duplicates, fixing stalled torrents, and all the other crap that comes with running a media server.

this thing handles everything. discovers new content based on what i actually like, downloads it through a vpn, imports it to plex, encodes it to save space, and keeps itself alive with a bunch of watchdog timers. i haven't touched it manually in weeks.

## what it actually does

- watches plex and goes "oh you have a lot of sci-fi and horror? here's more"
- scans tmdb using actors/directors/genres you tell it about
- fills in missing episodes of shows you're watching (complete seasons, not random eps)
- finds sequels/prequels to movies you own
- downloads through two qbittorrent instances (both behind vpns)
- imports completed downloads to plex within a minute
- runs tdarr to encode everything to hevc (saves like 40% space)
- cleans up dead torrents, duplicates, fake files automatically
- protects your drives from filling up (slows down, then stops if needed)
- backs everything up nightly

## setup

you need a linux server with docker, python 3, systemd, and some media drives.

```bash
git clone https://github.com/yuhboiililtesti/media-pipeline
cd media-pipeline
```

drop your api keys into the scripts (there's placeholders for everything). point the paths at your drives. install the systemd timers. that's basically it.

## the commands

```
pipeline max           send it (50 simultaneous downloads)
pipeline med           chill mode for when people are home
pipeline soft          pause everything (gaming, etc)

pipeline-grow          find new stuff based on your taste
pipeline-backlog       fill in missing episodes and sequels
pipeline-flow          do all of it at once

pipeline-clean         nuke dead torrents and free up space
pipeline-seed          inject trackers into everything, find more peers
pipeline-stall         figure out why the hell nothing is downloading
pipeline-unstall       emergency restart everything button

pipeline-health        quick check that everything's alive
pipeline-audit         deep dive into every component
pipeline-help          all 25 commands with examples
```

## stuff it protects against

| problem | how it fixes itself |
|---|---|
| vpn drops | restarts gluetun every 60 seconds if it's down |
| container dies | checks every 5min, restarts anything dead |
| torrent stuck at 99% | force rechecks near-complete stalled torrents |
| disk getting full | warns at 90%, slows downloads at 95%, stops at 98% |
| duplicate downloads | removes same-episode dupes every 30min (keeps the x265 one) |
| fake/corrupt files | scans daily for 0-byte or archive-disguised-as-media files |
| qbit loses config | nightly backup saves everything |
| radarr/sonarr miss an import | backup import watchdog catches it |

## the schedule (runs itself)

```
4am     pipeline max       nobody's awake, full send
12pm    pipeline med       people are home, chill
2am     discovery engine   scan tmdb, find new stuff
3am     nightly backup     save everything
3:30am  integrity check    scan for fake files
sun 3am dedup              weekly cleanup of duplicate media
```

## files you'll want to edit

- `safeguards/rules.json` — thresholds, limits, what to never download
- `plexlist.txt` — your taste seeds (actors you like, directors, genres, franchises)
- `taste/` — per-user taste profiles with genre/actor/director scores

## why i built this

i have a server with a 3090 ti and a bunch of storage. i wanted my plex library to grow on its own based on what i actually watch and like. not just random trending garbage. this pipeline watches what's in my library, cross-references it with tmdb, and goes "hey you have every christopher nolan movie except tenet — want me to grab it?"

also i was tired of waking up to find my drives full with no warning, or 500 stalled torrents clogging the queue, or the same episode downloaded 3 times from different indexers. this fixes all of that.

## requirements

- any linux server with docker
- radarr + sonarr + prowlarr (docker containers)
- plex media server
- qbittorrent (i run two — one on the server, one on a separate laptop both behind vpns)
- a tmdb api key (free, takes 2 minutes to get)
- some nvidia gpu helps for tdarr encoding but not required
- systemd (for all the timers)

## license

mit. do whatever you want with it. if it breaks something that's on you.
