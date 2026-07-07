#!/bin/bash
# Runs after discovery-engine to mark downloaded items
python3 /mnt/20TB/homelab/media/Pipeline/scripts/sync-plexlist.py
/usr/bin/python3 /mnt/20TB/homelab/media/Pipeline/scripts/update-havelist.py
