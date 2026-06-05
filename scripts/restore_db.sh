#!/usr/bin/env bash
#
# Restore the Postgres database from a gzip-compressed pg_dump.
#
# Usage:
#   ./scripts/restore_db.sh backups/timetable_db_20260605_120000.sql.gz
#
# WARNING: this overwrites the current database. You will be asked to confirm.
#
set -euo pipefail

DUMP_FILE="${1:?Usage: ./scripts/restore_db.sh <dump.sql.gz>}"
DB_NAME="${POSTGRES_DB:-timetable_db}"
DB_USER="${POSTGRES_USER:-postgres}"

if [[ ! -f "$DUMP_FILE" ]]; then
  echo "[restore] file not found: $DUMP_FILE" >&2
  exit 1
fi

read -r -p "This will OVERWRITE database '$DB_NAME'. Type 'yes' to continue: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
  echo "[restore] aborted."
  exit 1
fi

echo "[restore] recreating schema on '$DB_NAME'"
docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "[restore] loading $DUMP_FILE"
gunzip -c "$DUMP_FILE" | docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME"

echo "[restore] done. Consider running: docker compose exec backend flask db upgrade"
