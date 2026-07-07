#!/bin/bash
# Auto-generate plexlist.txt from current disk + Radarr/Sonarr state
set -euo pipefail

PL="/mnt/20TB/homelab/media/Pipeline/plexlist.txt"
LOG="/mnt/20TB/homelab/media/Pipeline/logs/generate-plexlist.log"

log() { echo "$(date '+%H:%M:%S') $1" | tee -a "$LOG"; }

log "Generating plexlist from current state..."

python3 -c "
import os, re

output = []
output.append('# PLEXLIST.TXT — Auto-generated: ' + __import__('time').strftime('%Y-%m-%d %H:%M'))
output.append('')
output.append('[MOVIES]')
for base in ['/mnt/20TB/Movies 1', '/mnt/20TB/Movies 4', '/mnt/8TB/Movies 2']:
    if os.path.isdir(base):
        for d in sorted(os.listdir(base)):
            if os.path.isdir(os.path.join(base, d)) and not d.startswith('.'):
                output.append(d)
output.append('')
output.append('[SHOWS]')
for base in ['/mnt/20TB/TV Shows 1', '/mnt/8TB/TV Shows 2']:
    if os.path.isdir(base):
        for d in sorted(os.listdir(base)):
            if os.path.isdir(os.path.join(base, d)) and not d.startswith('.'):
                output.append(d)
output.append('')
output.append('[ACTORS]')
output.append('[DIRECTORS]')
output.append('[FRANCHISES]')

with open('$PL', 'w') as f:
    f.write(chr(10).join(output))
log(f'Wrote ' + str(len(output)) + ' lines to plexlist.txt')
"
