#!/bin/sh
set -e

# Database backup script for emisofia.db
# Runs an atomic SQLite backup, uploads to S3, and cleans up.

DB_PATH="/data/emisofia.db"
BACKUP_FILE="/tmp/emisofia-$(date +%Y%m%d).db"
S3_DEST="s3://emisofia-backups/db/"

log() {
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $1"
}

log "Starting database backup..."

# 1. Create an atomic SQLite backup
if sqlite3 "$DB_PATH" ".backup $BACKUP_FILE"; then
  log "SQLite backup created: $BACKUP_FILE"
else
  log "ERROR: SQLite backup failed"
  exit 1
fi

# 2. Upload to S3
if aws s3 cp "$BACKUP_FILE" "$S3_DEST"; then
  log "Backup uploaded to $S3_DEST"
else
  log "ERROR: S3 upload failed"
  rm -f "$BACKUP_FILE"
  exit 1
fi

# 3. Clean up the temp file
rm -f "$BACKUP_FILE"
log "Temp file removed. Backup complete."
