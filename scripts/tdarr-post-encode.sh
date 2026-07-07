#!/bin/bash
# tdarr-post-encode.sh — Move completed encodes from cache to library
# Only touches /mnt/20TB/Encode-Tmp (Tdarr cache)
# Destinations: Movies → Movie dirs, TV → TV dirs
set -euo pipefail

LOG="/mnt/20TB/homelab/media/Pipeline/logs/tdarr-post-encode.log"
CACHE="/mnt/20TB/Encode-Tmp"
MOVIE_DIRS=("/mnt/20TB/Movies 1" "/mnt/20TB/Movies 4" "/mnt/8TB/Movies 2")
TV_DIRS=("/mnt/20TB/TV Shows 1" "/mnt/8TB/TV Shows 2")

log() { echo "$(date '+%H:%M:%S') $1" | tee -a "$LOG"; }

log "=== tdarr post-encode scan ==="
moved=0

# Find loose media files in cache (not in subdirs)
find "$CACHE" -maxdepth 1 -type f \( -iname "*.mkv" -o -iname "*.mp4" -o -iname "*.avi" \) 2>/dev/null | while read -r file; do
    name=$(basename "$file")
    size=$(stat -c%s "$file" 2>/dev/null || echo 0)
    [[ "$size" -lt 1048576 ]] && continue  # skip files under 1MB
    
    # Determine if movie or TV and find destination folder
    dest=""
    # Try TV first (episode pattern SxxExx)
    if echo "$name" | grep -qiE '[Ss][0-9]{2}[Ee][0-9]{2}'; then
        # Extract show name before SxxExx
        show=$(echo "$name" | sed -E 's/[\._-]*[Ss][0-9]{2}[Ee][0-9]{2}.*//' | sed 's/[\._-]/ /g' | sed 's/  */ /g')
        for tvdir in "${TV_DIRS[@]}"; do
            match=$(find "$tvdir" -maxdepth 1 -type d -iname "*${show}*" 2>/dev/null | head -1)
            if [[ -n "$match" ]]; then
                dest="$match"
                break
            fi
        done
    fi
    
    # Try Movies (no SxxExx pattern)
    if [[ -z "$dest" ]]; then
        year=$(echo "$name" | grep -oP '\b(19|20)\d{2}\b' | head -1)
        if [[ -n "$year" ]]; then
            title=$(echo "$name" | sed -E "s/\b${year}\b.*//" | sed 's/[\._-]/ /g' | sed 's/  */ /g' | xargs)
            for movdir in "${MOVIE_DIRS[@]}"; do
                match=$(find "$movdir" -maxdepth 1 -type d -iname "*${title}*${year}*" 2>/dev/null | head -1)
                if [[ -n "$match" ]]; then
                    dest="$match"
                    break
                fi
            done
        fi
    fi
    
    if [[ -n "$dest" ]]; then
        # Check for existing file in destination
        existing=$(find "$dest" -maxdepth 1 -type f \( -iname "*.mkv" -o -iname "*.mp4" \) 2>/dev/null | head -1)
        if [[ -n "$existing" ]]; then
            old_size=$(stat -c%s "$existing" 2>/dev/null || echo 0)
            if [[ "$size" -lt "$old_size" ]] || echo "$name" | grep -qi 'hevc\|x265\|h265'; then
                # Encoded is smaller or HEVC — replace original
                rm -f "$existing"
                mv "$file" "$dest/"
                saved=$(( (old_size - size) / 1048576 ))
                log "REPLACED: $(basename "$dest") — saved ${saved}MB"
                moved=$((moved + 1))
            else
                # Keep original, discard cache copy
                rm -f "$file"
            fi
        else
            # No existing — just move in
            mv "$file" "$dest/"
            log "ADDED: $(basename "$dest")/$name"
            moved=$((moved + 1))
        fi
    fi
done

# Clean empty subdirs in cache
find "$CACHE" -mindepth 1 -maxdepth 1 -type d -empty -delete 2>/dev/null

# Refresh Plex
curl -s -H "X-Plex-Token: BJm8tFoMaeXaUn2xabWJ" \
    "http://localhost:32400/library/sections/3/refresh?force=0" 2>/dev/null || true

log "Done — processed $moved files"
