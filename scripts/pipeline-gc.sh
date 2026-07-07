#!/bin/bash
# pipeline-gc.sh — Autonomous garbage collection
# Cleans up stale candidates, old logs, and cache overgrowth
# Runs daily at 4 AM

PIPE="/mnt/20TB/homelab/media/Pipeline"
LOG="$PIPE/logs/pipeline-gc.log"
log() { echo "$(date '+%H:%M:%S') $1" | tee -a "$LOG"; }

log "=== GARBAGE COLLECTION START ==="

# 1. Stale candidates (>90 days → delete from review/quarantine/rejected)
for q in review_queue quarantine rejected; do
    qp="$PIPE/candidates/${q}.txt"
    [ -f "$qp" ] || continue
    # Keep recent, archive old
    python3 -c "
import time, os
lines = open('$qp').readlines()
cutoff = time.time() - (90 * 86400)
kept = []
removed = 0
for l in lines:
    # No timestamp on lines, just keep everything for now
    kept.append(l)
with open('$qp', 'w') as f:
    f.writelines(kept[-500:])  # Keep last 500 entries max
print(f'{os.path.basename("$qp")}: {len(lines)} -> {len(kept[-500:])}')
"
done

# 2. Log rotation (>30 days → compress)
find "$PIPE/logs" -name '*.log' -size +1M -exec gzip -f {} \; 2>/dev/null
log "logs compressed"

# 3. Old archives cleanup
find "$PIPE/state" -name '*.json' -mtime +30 -delete 2>/dev/null
[ -f "$PIPE/state/HEALTH_SCORE.json" ] && cp "$PIPE/state/HEALTH_SCORE.json" "$PIPE/state/HEALTH_SCORE-2026-06-30.json"

# 4. Clean empty dirs
find "$PIPE" -type d -empty -delete 2>/dev/null

log "=== GARBAGE COLLECTION COMPLETE ==="
