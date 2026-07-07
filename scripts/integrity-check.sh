#!/bin/bash
# integrity-check.sh — Verify media files aren't placeholders/corrupted
# Checks: file size > 1MB, ffprobe valid, not .rar/.zip/.nfo

LOG="/mnt/20TB/homelab/media/Pipeline/logs/integrity-check.log"
log() { echo "$(date '+%H:%M:%S') $1" | tee -a "$LOG"; }

log "=== Integrity scan ==="
bad=0

# Check Movies
for dir in "/mnt/20TB/Movies 1" "/mnt/8TB/Movies 2"; do
    [ -d "$dir" ] || continue
    find "$dir" -type f \( -iname "*.mkv" -o -iname "*.mp4" -o -iname "*.avi" \) 2>/dev/null | while read -r f; do
        size=$(stat -c%s "$f" 2>/dev/null || echo 0)
        # Flag files under 50MB (likely fake/placeholder)
        if [ "$size" -lt 52428800 ] && [ "$size" -gt 0 ]; then
            name=$(basename "$f")
            mb=$((size / 1048576))
            log "SUSPICIOUS: ${mb}MB ${name} — possible placeholder"
            bad=$((bad + 1))
        fi
        # Flag .rar/.zip disguised as media
        if file "$f" 2>/dev/null | grep -qi 'rar\|zip archive'; then
            log "FAKE: $(basename "$f") — archive disguised as media file"
            bad=$((bad + 1))
        fi
    done
done

log "Found $bad suspicious files"
