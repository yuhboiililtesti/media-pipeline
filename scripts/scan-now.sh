#!/bin/bash
# scan-now.sh — Run discovery engine immediately from anywhere

if [ -f /mnt/20TB/homelab/media/Pipeline/discovery/engine.py ]; then
    # Running on server directly
    cd /mnt/20TB/homelab/media/Pipeline
    TMDB_KEY=YOUR_TMDB_API_KEY PYTHONPATH=/mnt/20TB/homelab/media/Pipeline python3 /mnt/20TB/homelab/media/Pipeline/discovery/engine.py "${1:-daily}"
else
    # Running from desktop/laptop — SSH to server
    echo 'Running via SSH to server...'
    ssh server "TMDB_KEY=YOUR_TMDB_API_KEY PYTHONPATH=/mnt/20TB/homelab/media/Pipeline python3 /mnt/20TB/homelab/media/Pipeline/discovery/engine.py ${1:-daily}"
fi

echo
echo '=== DONE ==='
echo 'Check: ssh server tail /mnt/20TB/homelab/media/Pipeline/logs/discovery-engine.log'
