# API REFERENCE — Every API Endpoint
# ⚠ ALL API KEYS REDACTED — see /home/topaz/home/info for actual values
# Keys shown as RADARR_KEY, SONARR_KEY, etc. — replace with real values from info file

# API REFERENCE — Every API Endpoint, Key, and Example

## API Keys
```
Radarr:   RADARR_KEY
Sonarr:   SONARR_KEY
Prowlarr: PROWLARR_KEY
TMDB:     TMDB_KEY (free tier)
Plex:     PLEX_TOKEN
```

## Radarr API (http://localhost:7878/api/v3)

```bash
KEY=RADARR_KEY

# System status
curl -s http://localhost:7878/api/v3/system/status?apikey=$KEY

# All movies
curl -s http://localhost:7878/api/v3/movie?apikey=$KEY

# Single movie
curl -s http://localhost:7878/api/v3/movie/123?apikey=$KEY

# Download queue
curl -s http://localhost:7878/api/v3/queue?apikey=$KEY

# History
curl -s http://localhost:7878/api/v3/history?apikey=$KEY&pageSize=10&sortKey=date&sortDirection=descending

# Download client
curl -s http://localhost:7878/api/v3/downloadclient?apikey=$KEY

# Remote path mappings
curl -s http://localhost:7878/api/v3/remotepathmapping?apikey=$KEY

# Root folders
curl -s http://localhost:7878/api/v3/rootfolder?apikey=$KEY

# Health warnings
curl -s http://localhost:7878/api/v3/health?apikey=$KEY

# Quality profiles
curl -s http://localhost:7878/api/v3/qualityprofile?apikey=$KEY

# Commands
# MissingMoviesSearch
curl -s -X POST http://localhost:7878/api/v3/command?apikey=$KEY -H 'Content-Type:application/json' -d '{"name":"MissingMoviesSearch"}'

# DownloadedMoviesScan
curl -s -X POST http://localhost:7878/api/v3/command?apikey=$KEY -H 'Content-Type:application/json' -d '{"name":"DownloadedMoviesScan","importMode":"move"}'

# RefreshMovie
curl -s -X POST http://localhost:7878/api/v3/command?apikey=$KEY -H 'Content-Type:application/json' -d '{"name":"RefreshMovie","movieIds":[123]}'

# RescanMovie
curl -s -X POST http://localhost:7878/api/v3/command?apikey=$KEY -H 'Content-Type:application/json' -d '{"name":"RescanMovie","movieIds":[123]}'

# Add movie
curl -s -X POST http://localhost:7878/api/v3/movie?apikey=$KEY -H 'Content-Type:application/json' -d '{"tmdbId":123,"qualityProfileId":6,"monitored":true,"rootFolderPath":"/mnt/20TB/Movies 1","addOptions":{"searchForMovie":true}}'

# Update movie (unmonitor)
curl -s -X PUT http://localhost:7878/api/v3/movie/editor?apikey=$KEY -H 'Content-Type:application/json' -d '{"movieIds":[123],"monitored":false}'

# Update movie (change root folder)
curl -s -X PUT http://localhost:7878/api/v3/movie/editor?apikey=$KEY -H 'Content-Type:application/json' -d '{"movieIds":[123],"rootFolderPath":"/mnt/20TB/Movies 4/"}'

# Delete movie
curl -s -X DELETE http://localhost:7878/api/v3/movie/123?apikey=$KEY
```

## Sonarr API (http://localhost:8989/api/v3)

```bash
KEY=SONARR_KEY

# System status
curl -s http://localhost:8989/api/v3/system/status?apikey=$KEY

# All series
curl -s http://localhost:8989/api/v3/series?apikey=$KEY

# Series lookup (search)
curl -s "http://localhost:8989/api/v3/series/lookup?apikey=$KEY&term=Rick+and+Morty"

# Series lookup by TMDB
curl -s "http://localhost:8989/api/v3/lookup?apikey=$KEY&term=tmdb:60625"

# Download queue
curl -s http://localhost:8989/api/v3/queue?apikey=$KEY

# Wanted/missing episodes
curl -s http://localhost:8989/api/v3/wanted/missing?apikey=$KEY&pageSize=100

# Download client
curl -s http://localhost:8989/api/v3/downloadclient?apikey=$KEY

# Remote path mappings
curl -s http://localhost:8989/api/v3/remotepathmapping?apikey=$KEY

# Root folders
curl -s http://localhost:8989/api/v3/rootfolder?apikey=$KEY

# Commands
# SeriesSearch
curl -s -X POST http://localhost:8989/api/v3/command?apikey=$KEY -H 'Content-Type:application/json' -d '{"name":"SeriesSearch","seriesId":123}'

# DownloadedEpisodesScan
curl -s -X POST http://localhost:8989/api/v3/command?apikey=$KEY -H 'Content-Type:application/json' -d '{"name":"DownloadedEpisodesScan","importMode":"move"}'

# RefreshSeries
curl -s -X POST http://localhost:8989/api/v3/command?apikey=$KEY -H 'Content-Type:application/json' -d '{"name":"RefreshSeries"}'

# Add series
curl -s -X POST http://localhost:8989/api/v3/series?apikey=$KEY -H 'Content-Type:application/json' -d '{"tvdbId":123,"title":"Show Name","qualityProfileId":3,"monitored":true,"rootFolderPath":"/mnt/20TB/TV Shows 1","addOptions":{"searchForMissingEpisodes":true}}'
```

## Prowlarr API (http://localhost:9696/api/v1)

```bash
KEY=PROWLARR_KEY

# All indexers
curl -s http://localhost:9696/api/v1/indexer?apikey=$KEY

# Enable/disable indexer
curl -s -X PUT http://localhost:9696/api/v1/indexer/5?apikey=$KEY -H 'Content-Type:application/json' -d '{"enable":false,...}'

# Add indexer (TorrentRss)
curl -s -X POST http://localhost:9696/api/v1/indexer?apikey=$KEY -H 'Content-Type:application/json' -d '{"name":"EZTV","enable":true,"protocol":"torrent","implementation":"TorrentRssIndexer","configContract":"TorrentRssIndexerSettings","fields":[{"name":"baseUrl","value":"https://eztvx.to"}],"categories":[5000]}'
```

## Plex API (http://localhost:32400)

```bash
TOKEN=PLEX_TOKEN

# Server identity
curl -s "http://localhost:32400/identity?X-Plex-Token=$TOKEN"

# Library sections
curl -s "http://localhost:32400/library/sections?X-Plex-Token=$TOKEN"

# All movies
curl -s "http://localhost:32400/library/sections/3/all?type=1&X-Plex-Token=$TOKEN"

# All TV shows
curl -s "http://localhost:32400/library/sections/5/all?X-Plex-Token=$TOKEN"

# Show details (seasons)
curl -s "http://localhost:32400/library/metadata/12345/children?X-Plex-Token=$TOKEN"

# Season episodes
curl -s "http://localhost:32400/library/metadata/67890/children?X-Plex-Token=$TOKEN"

# Refresh library
curl -s "http://localhost:32400/library/sections/3/refresh?X-Plex-Token=$TOKEN"

# Active sessions
curl -s "http://localhost:32400/status/sessions?X-Plex-Token=$TOKEN"

# Set preferences
curl -s -X PUT "http://localhost:32400/:/prefs?PlexOnlineHome=0" -H "X-Plex-Token: $TOKEN"

# User accounts
curl -s "http://localhost:32400/accounts?X-Plex-Token=$TOKEN"

# Plex.tv shared users
curl -s "https://plex.tv/api/users?X-Plex-Token=$TOKEN"
```

## qBittorrent API (http://10.0.0.234:8080/api/v2)

```bash
USER=topaz; PASS=(see info file)

# Login (needed for all other calls)
curl -c /tmp/qb -L http://10.0.0.234:8080/api/v2/auth/login --data-urlencode "username=$USER" --data-urlencode "password=$PASS"

# Transfer info
curl -b /tmp/qb http://10.0.0.234:8080/api/v2/transfer/info

# All torrents
curl -b /tmp/qb http://10.0.0.234:8080/api/v2/torrents/info

# Filtered (completed, downloading, stalled, paused, errored)
curl -b /tmp/qb "http://10.0.0.234:8080/api/v2/torrents/info?filter=completed"

# Preferences
curl -b /tmp/qb http://10.0.0.234:8080/api/v2/app/preferences

# Set preferences
curl -b /tmp/qb http://10.0.0.234:8080/api/v2/app/setPreferences -d 'json={"max_active_downloads":15}'

# Add trackers
curl -b /tmp/qb -X POST http://10.0.0.234:8080/api/v2/torrents/addTrackers --data-urlencode "hash=ABC" --data-urlencode "urls=udp://tracker..."

# Re-announce
curl -b /tmp/qb -X POST http://10.0.0.234:8080/api/v2/torrents/reannounce --data-urlencode "hashes=ABC|DEF"

# Force recheck
curl -b /tmp/qb -X POST http://10.0.0.234:8080/api/v2/torrents/recheck --data-urlencode "hashes=ABC"

# Resume
curl -b /tmp/qb -X POST http://10.0.0.234:8080/api/v2/torrents/resume --data-urlencode "hashes=ABC"

# Delete (keep files)
curl -b /tmp/qb -X POST http://10.0.0.234:8080/api/v2/torrents/delete --data-urlencode "hashes=ABC" --data-urlencode "deleteFiles=false"

# Torrent trackers
curl -b /tmp/qb "http://10.0.0.234:8080/api/v2/torrents/trackers?hash=ABC"

# Change password
curl -b /tmp/qb http://10.0.0.234:8080/api/v2/app/setPreferences -d 'json={"web_ui_password":"newpass"}'
```

## TMDB API (https://api.themoviedb.org/3)

```bash
KEY=TMDB_KEY

# Search movie
curl -s "https://api.themoviedb.org/3/search/movie?api_key=$KEY&query=Inception"

# Search TV
curl -s "https://api.themoviedb.org/3/search/tv?api_key=$KEY&query=Breaking+Bad"

# Search person
curl -s "https://api.themoviedb.org/3/search/person?api_key=$KEY&query=Christopher+Nolan"

# Search collection
curl -s "https://api.themoviedb.org/3/search/collection?api_key=$KEY&query=Star+Wars"

# Movie details
curl -s "https://api.themoviedb.org/3/movie/27205?api_key=$KEY"

# Movie credits
curl -s "https://api.themoviedb.org/3/movie/27205/credits?api_key=$KEY"

# Person movie credits
curl -s "https://api.themoviedb.org/3/person/525/movie_credits?api_key=$KEY"

# Collection
curl -s "https://api.themoviedb.org/3/collection/10?api_key=$KEY"

# Similar movies
curl -s "https://api.themoviedb.org/3/movie/27205/recommendations?api_key=$KEY"

# Discover by genre
curl -s "https://api.themoviedb.org/3/discover/movie?api_key=$KEY&with_genres=878&sort_by=popularity.desc"

# Trending
curl -s "https://api.themoviedb.org/3/trending/movie/week?api_key=$KEY"

# Popular
curl -s "https://api.themoviedb.org/3/movie/popular?api_key=$KEY"

# Genre list
curl -s "https://api.themoviedb.org/3/genre/movie/list?api_key=$KEY"
```
