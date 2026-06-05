#!/usr/bin/env bash
#
# Back up the Postgres database to a timestamped, gzip-compressed dump.
#
# Usage:
#   ./scripts/backup_db.sh [output_dir]
#
# Defaults to ./backups. Runs pg_dump inside the compose `postgres` service so
# it works without a local postgres client. Safe to run on a cron schedule.
#
set -euo pipefail

OUT_DIR="${1:-./backups}"
DB_NAME="${POSTGRES_DB:-timetable_db}"
DB_USER="${POSTGRES_USER:-postgres}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="$OUT_DIR/${DB_NAME}_${STAMP}.sql.gz"

echo "[backup] dumping '$DB_NAME' -> $OUT_FILE"
docker compose exec -T postgres pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$OUT_FILE"

echo "[backup] pruning dumps older than ${RETENTION_DAYS} days"
find "$OUT_DIR" -name "${DB_NAME}_*.sql.gz" -type f -mtime "+${RETENTION_DAYS}" -delete || true

echo "[backup] done: $(du -h "$OUT_FILE" | cut -f1) $OUT_FILE"
