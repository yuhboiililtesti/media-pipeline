#!/bin/bash
set -euo pipefail
# nightly-backup.sh — Export ALL configs, databases, scripts nightly at 3 AM
# Copies archive to desktop /mnt/500gb-1/homelab-backup/

LOG="/mnt/20TB/homelab/media/Pipeline/logs/nightly-backup.log"
DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/tmp/homelab-backup-$DATE"
DESKTOP="topaz@10.0.0.192"
DESKTOP_PATH="/mnt/500gb-1/homelab-backup"
KEEP_DAYS=7

log() { echo "$(date '+%H:%M:%S') $1" | tee -a "$LOG"; }

log "=========================================="
log "NIGHTLY BACKUP STARTING"

mkdir -p "$BACKUP_DIR"/{docker,configs,systemd-server,systemd-laptop,scripts-server,scripts-laptop,network,inventory}
mkdir -p "$BACKUP_DIR"/configs/radarr "$BACKUP_DIR"/configs/sonarr "$BACKUP_DIR"/configs/prowlarr

# --- 1. EXPORT ARR BACKUPS ---
log "Exporting Radarr backup..."
curl -s -X POST "http://localhost:7878/api/v3/command" \
    -H "X-Api-Key: YOUR_RADARR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"name":"Backup"}' > /dev/null 2>&1
sleep 5
# Copy latest backup
latest_radarr=$(ls -t /mnt/20TB/homelab/media/compose/radarr/Backups/scheduled/ 2>/dev/null | head -1)
if [ -n "$latest_radarr" ]; then
    cp "/mnt/20TB/homelab/media/compose/radarr/Backups/scheduled/$latest_radarr" "$BACKUP_DIR/configs/radarr/" 2>/dev/null
    log "  Radarr: $latest_radarr"
fi

log "Exporting Sonarr backup..."
curl -s -X POST "http://localhost:8989/api/v3/command" \
    -H "X-Api-Key: YOUR_SONARR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"name":"Backup"}' > /dev/null 2>&1
sleep 5
latest_sonarr=$(ls -t /mnt/20TB/homelab/media/compose/sonarr2/Backups/scheduled/ 2>/dev/null | head -1)
if [ -n "$latest_sonarr" ]; then
    cp "/mnt/20TB/homelab/media/compose/sonarr2/Backups/scheduled/$latest_sonarr" "$BACKUP_DIR/configs/sonarr/" 2>/dev/null
    log "  Sonarr: $latest_sonarr"
fi

log "Exporting Prowlarr backup..."
curl -s -X POST "http://localhost:9696/api/v1/command" \
    -H "X-Api-Key: YOUR_PROWLARR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"name":"Backup"}' > /dev/null 2>&1
sleep 5
latest_prowlarr=$(ls -t /mnt/20TB/homelab/media/compose/prowlarr/Backups/scheduled/ 2>/dev/null | head -1)
if [ -n "$latest_prowlarr" ]; then
    cp "/mnt/20TB/homelab/media/compose/prowlarr/Backups/scheduled/$latest_prowlarr" "$BACKUP_DIR/configs/prowlarr/" 2>/dev/null
    log "  Prowlarr: $latest_prowlarr"
fi

# --- 2. COPY CONFIG FILES ---
log "Copying config files..."
cp /mnt/20TB/homelab/media/compose/docker-compose.yml "$BACKUP_DIR/docker/server-compose.yml" 2>/dev/null
sudo cp /var/lib/plex/Plex\ Media\ Server/Preferences.xml "$BACKUP_DIR/configs/plex-preferences.xml" 2>/dev/null || true
cp /etc/fstab "$BACKUP_DIR/network/fstab-server" 2>/dev/null
cp /etc/exports "$BACKUP_DIR/network/exports" 2>/dev/null
cp /etc/ssh/sshd_config "$BACKUP_DIR/network/sshd_config" 2>/dev/null
cp /etc/samba/creds-arch-server "$BACKUP_DIR/configs/samba-creds" 2>/dev/null || true
sudo ufw status verbose > "$BACKUP_DIR/network/ufw-status.txt" 2>/dev/null || true
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,UUID > "$BACKUP_DIR/inventory/lsblk-server.txt" 2>/dev/null

# --- 3. COPY SYSTEMD FILES ---
log "Copying systemd files..."
cp /etc/systemd/system/*.service "$BACKUP_DIR/systemd-server/" 2>/dev/null || true
cp /etc/systemd/system/*.timer "$BACKUP_DIR/systemd-server/" 2>/dev/null || true
cp /etc/systemd/system/*.mount "$BACKUP_DIR/systemd-server/" 2>/dev/null || true
cp /etc/systemd/system/*.conf "$BACKUP_DIR/systemd-server/" 2>/dev/null || true

# --- 4. COPY SCRIPTS ---
log "Copying scripts..."
cp /usr/local/bin/*.sh "$BACKUP_DIR/scripts-server/" 2>/dev/null || true
cp /usr/local/bin/*.py "$BACKUP_DIR/scripts-server/" 2>/dev/null || true

# --- 5. PULL FROM LAPTOP ---
log "Pulling laptop configs..."
ssh -p 2225 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    laptop@10.0.0.234 "tar czf /tmp/laptop-backup.tar.gz \
    /home/laptop/pipeline/docker-compose.yml \
    /home/laptop/pipeline/*.sh \
    /home/laptop/pipeline/config/ \
    /etc/fstab \
    /etc/systemd/system/*.service \
    /etc/systemd/system/*.timer \
    /etc/systemd/network/*.network \
    /etc/systemd/system/docker.service.d/nfs-wait.conf \
    2>/dev/null" 2>/dev/null

scp -P 2225 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    laptop@10.0.0.234:/tmp/laptop-backup.tar.gz "$BACKUP_DIR/laptop-backup.tar.gz" 2>/dev/null && \
    log "  Laptop backup pulled" || log "  Laptop unreachable — skipping"

lsblk_output=$(ssh -p 2225 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    laptop@10.0.0.234 "lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE 2>/dev/null" 2>/dev/null)
[ -n "$lsblk_output" ] && echo "$lsblk_output" > "$BACKUP_DIR/inventory/lsblk-laptop.txt"

# --- 6. COPY SSH CONFIG ---
cp ~/.ssh/config "$BACKUP_DIR/network/ssh-config" 2>/dev/null || true

# --- 7. CREATE ARCHIVE ---
log "Creating archive..."
ARCHIVE_NAME="homelab-backup-$DATE.tar.gz"
tar czf "/tmp/$ARCHIVE_NAME" -C /tmp "homelab-backup-$DATE" 2>/dev/null

# --- 8. COPY TO DESKTOP ---
log "Copying to desktop /mnt/500gb-1/homelab-backup/..."
ssh -p 2224 -o StrictHostKeyChecking=no -o ConnectTimeout=10 topaz@10.0.0.192 \
    "mkdir -p $DESKTOP_PATH/archives" 2>/dev/null

scp -P 2224 -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "/tmp/$ARCHIVE_NAME" "$DESKTOP:$DESKTOP_PATH/archives/" 2>/dev/null && \
    log "  Copied to desktop" || log "  Desktop unreachable — archive on server only"

# Also copy live configs to desktop
rsync -a --delete -e "ssh -p 2224 -o StrictHostKeyChecking=no -o ConnectTimeout=10" \
    "$BACKUP_DIR/docker/" "$DESKTOP:$DESKTOP_PATH/docker/" 2>/dev/null
rsync -a --delete -e "ssh -p 2224 -o StrictHostKeyChecking=no -o ConnectTimeout=10" \
    "$BACKUP_DIR/configs/" "$DESKTOP:$DESKTOP_PATH/configs/" 2>/dev/null
rsync -a --delete -e "ssh -p 2224 -o StrictHostKeyChecking=no -o ConnectTimeout=10" \
    "$BACKUP_DIR/systemd-server/" "$DESKTOP:$DESKTOP_PATH/systemd/server/" 2>/dev/null
rsync -a --delete -e "ssh -p 2224 -o StrictHostKeyChecking=no -o ConnectTimeout=10" \
    "$BACKUP_DIR/scripts-server/" "$DESKTOP:$DESKTOP_PATH/scripts/server/" 2>/dev/null
rsync -a --delete -e "ssh -p 2224 -o StrictHostKeyChecking=no -o ConnectTimeout=10" \
    "$BACKUP_DIR/network/" "$DESKTOP:$DESKTOP_PATH/network/" 2>/dev/null
rsync -a --delete -e "ssh -p 2224 -o StrictHostKeyChecking=no -o ConnectTimeout=10" \
    "$BACKUP_DIR/inventory/" "$DESKTOP:$DESKTOP_PATH/inventory/" 2>/dev/null

# --- 9. CLEANUP OLD ARCHIVES ---
log "Cleaning old archives..."
find /tmp -name "homelab-backup-*.tar.gz" -mtime +$KEEP_DAYS -delete 2>/dev/null
find "$BACKUP_DIR" -delete 2>/dev/null || rm -rf "$BACKUP_DIR" 2>/dev/null

# Clean old on desktop too
ssh -p 2224 -o StrictHostKeyChecking=no -o ConnectTimeout=10 topaz@10.0.0.192 \
    "find $DESKTOP_PATH/archives -name 'homelab-backup-*.tar.gz' -mtime +$KEEP_DAYS -delete" 2>/dev/null

log "Nightly backup complete — archive: $ARCHIVE_NAME"
log "=========================================="
