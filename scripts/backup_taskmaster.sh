#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${TASKMASTER_DB_PATH:-"$ROOT_DIR/data/taskmaster.sqlite3"}"
BACKUP_DIR="${TASKMASTER_BACKUP_DIR:-"$ROOT_DIR/data/backups"}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"

if [[ ! -f "$DB_PATH" ]]; then
  echo "Database not found: $DB_PATH" >&2
  exit 1
fi

sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/taskmaster-$STAMP.sqlite3'"
echo "$BACKUP_DIR/taskmaster-$STAMP.sqlite3"
