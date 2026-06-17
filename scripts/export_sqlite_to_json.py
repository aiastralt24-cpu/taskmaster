#!/usr/bin/env python3
"""Export the local Taskmaster SQLite data for a one-time Postgres import."""

import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "taskmaster.sqlite3"
DEFAULT_OUT = ROOT / "data" / "taskmaster-postgres-import.json"

EXPORT_TABLES = [
    "tasks",
    "users",
    "user_access",
    "activity_log",
    "task_comments",
    "task_assets",
    "approval_events",
    "notifications",
    "task_checklists",
    "system_audit",
]

PRIVATE_TABLES = {"sessions", "password_reset_tokens"}


def table_exists(conn, table):
    row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", [table]).fetchone()
    return row is not None


def rows_for_table(conn, table):
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
    return [dict(row) for row in rows]


def main():
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    if not db_path.exists():
        raise SystemExit(f"SQLite database not found: {db_path}")

    payload = {
        "source": str(db_path),
        "format": "taskmaster-sqlite-export-v1",
        "excludedTables": sorted(PRIVATE_TABLES),
        "tables": {},
    }

    with sqlite3.connect(db_path) as conn:
        for table in EXPORT_TABLES:
            payload["tables"][table] = rows_for_table(conn, table) if table_exists(conn, table) else []

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = {table: len(rows) for table, rows in payload["tables"].items()}
    print(f"Exported {db_path} -> {out_path}")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
