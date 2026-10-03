#!/usr/bin/env bash
# BuildOS AI backup (BUILD-141): the database AND the uploaded files.
#
# Documents and site photos live on disk (STORAGE_DIR), not in Postgres, so a
# database dump alone is not a complete backup.
#
# Usage (production stack, from the repo root):
#   deploy/backup.sh                 # writes to ./backups
#   BACKUP_DIR=/mnt/backups KEEP_DAYS=30 deploy/backup.sh
#
# Schedule it daily (cron: 0 2 * * * cd /srv/buildos && deploy/backup.sh) and copy
# ./backups somewhere off this machine; a backup on the same disk isn't one.
# Restore steps: deploy/OPERATIONS.md.

set -euo pipefail

COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.production"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$BACKUP_DIR"
db_file="$BACKUP_DIR/buildos-db-$STAMP.dump"
files_file="$BACKUP_DIR/buildos-files-$STAMP.tar.gz"

# Written under a temporary name and only renamed once complete and readable,
# so a half-finished file is never mistaken for a good backup.
echo "Dumping database..."
$COMPOSE exec -T db sh -c 'pg_dump --format=custom --no-owner -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$db_file.partial"
$COMPOSE exec -T db pg_restore --list < "$db_file.partial" > /dev/null
mv "$db_file.partial" "$db_file"

echo "Archiving uploaded files..."
$COMPOSE exec -T backend tar -czf - -C /app/storage_data . > "$files_file.partial"
tar -tzf "$files_file.partial" > /dev/null
mv "$files_file.partial" "$files_file"

echo "Removing backups older than $KEEP_DAYS days..."
find "$BACKUP_DIR" -name 'buildos-*' -type f -mtime +"$KEEP_DAYS" -delete

echo "Done:"
ls -lh "$db_file" "$files_file"
