#!/usr/bin/env python3
"""Import a Taskmaster SQLite JSON export into the Vercel/Neon Postgres database."""

import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import api.taskmaster as taskmaster_api  # noqa: E402

init_db = taskmaster_api.init_db
now_iso = taskmaster_api.now_iso
quote_ident = taskmaster_api.quote_ident


DEFAULT_IN = ROOT / "data" / "taskmaster-postgres-import.json"

TASK_FIELDS = [
    "id", "no", "brand", "bucket", "zone", "title", "length", "hook", "agency", "status", "owner",
    "bucketAdmin", "primaryOwner", "secondaryOwner", "reviewer", "deadline", "plannedStart",
    "publishDate", "actualCompletionDate", "delayReason", "assignmentStatus", "priority", "notes",
    "createdAt", "updatedAt", "completedAt", "lastStageChangedAt",
]

USER_FIELDS = [
    "id", "username", "displayName", "role", "email", "phone", "team", "agencyName", "isAgencyUser",
    "notificationPrefs", "passwordHash", "isActive", "mustChangePassword", "createdAt", "updatedAt",
]

DIRECT_TABLES = {
    "activity_log": ["id", "taskId", "action", "actorRole", "changedAt", "beforeJson", "afterJson"],
    "task_comments": ["id", "taskId", "userId", "body", "createdAt"],
    "task_assets": ["id", "taskId", "userId", "assetType", "label", "url", "createdAt"],
    "approval_events": ["id", "taskId", "userId", "decision", "note", "createdAt"],
    "notifications": ["id", "userId", "taskId", "title", "body", "channel", "deliveryStatus", "isRead", "createdAt"],
    "task_checklists": ["id", "taskId", "step", "isDone", "updatedBy", "updatedAt"],
    "system_audit": ["id", "actorUserId", "actorName", "action", "subjectType", "subjectId", "metadataJson", "createdAt"],
}


def database_url():
    value = os.environ.get("DATABASE_URL", "")
    if not value:
        raise SystemExit("DATABASE_URL is required. Pull it from Vercel/Neon before importing.")
    return value


def qmarks(values):
    return ",".join(["%s"] * len(values))


def coerce_bool(value):
    if isinstance(value, bool):
        return value
    if value in (1, "1", "true", "True", "TRUE", "yes", "on"):
        return True
    return False


def clean_row(row, fields):
    cleaned = {}
    for field in fields:
        value = row.get(field)
        if field in {"isAgencyUser", "isActive", "mustChangePassword", "isRead", "isDone"}:
            value = coerce_bool(value)
        if value is None and field in {"createdAt", "updatedAt", "changedAt"}:
            value = now_iso()
        if value is None:
            value = ""
        cleaned[field] = value
    return cleaned


def upsert(cur, table, row, fields, conflict="id"):
    cols = ", ".join(quote_ident(f) for f in fields)
    updates = ", ".join(f"{quote_ident(f)} = EXCLUDED.{quote_ident(f)}" for f in fields if f != conflict)
    cur.execute(
        f"INSERT INTO {table}({cols}) VALUES({qmarks(fields)}) ON CONFLICT ({quote_ident(conflict)}) DO UPDATE SET {updates}",
        [row[f] for f in fields],
    )


def reset_sequence(cur, table):
    cur.execute("SELECT pg_get_serial_sequence(%s, %s) AS seq", [table, "id"])
    row = cur.fetchone()
    if row and row["seq"]:
        cur.execute("SELECT setval(%s, COALESCE((SELECT MAX(id) FROM " + table + "), 0) + 1, false)", [row["seq"]])


def main():
    import_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IN
    if not import_path.exists():
        raise SystemExit(f"Import file not found: {import_path}")

    os.environ["DATABASE_URL"] = database_url()
    taskmaster_api.DATABASE_URL = os.environ["DATABASE_URL"]
    init_db()
    payload = json.loads(import_path.read_text(encoding="utf-8"))
    tables = payload.get("tables") or {}
    counts = {}

    with psycopg.connect(database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for table in [
                "activity_log",
                "task_comments",
                "task_assets",
                "approval_events",
                "notifications",
                "task_checklists",
                "system_audit",
                "tasks",
            ]:
                cur.execute(f"DELETE FROM {table}")

            for row in tables.get("users", []):
                upsert(cur, "users", clean_row(row, USER_FIELDS), USER_FIELDS)
                counts["users"] = counts.get("users", 0) + 1

            cur.execute("DELETE FROM user_access")
            for row in tables.get("user_access", []):
                cur.execute(
                    'INSERT INTO user_access("userId","accessType","accessValue") VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',
                    [row.get("userId") or row.get("user_id") or "", row.get("accessType") or "", row.get("accessValue") or ""],
                )
                counts["user_access"] = counts.get("user_access", 0) + 1

            for row in tables.get("tasks", []):
                upsert(cur, "tasks", clean_row(row, TASK_FIELDS), TASK_FIELDS)
                counts["tasks"] = counts.get("tasks", 0) + 1

            for table, fields in DIRECT_TABLES.items():
                for row in tables.get(table, []):
                    cleaned = clean_row(row, fields)
                    if not cleaned.get("id"):
                        continue
                    upsert(cur, table, cleaned, fields)
                    counts[table] = counts.get(table, 0) + 1
                if counts.get(table):
                    reset_sequence(cur, table)

            cur.execute("UPDATE users SET role = 'admin' WHERE role = 'super_admin' AND username != 'aniket'")
            cur.execute('UPDATE users SET role = %s, "isActive" = TRUE, "mustChangePassword" = TRUE, "updatedAt" = %s WHERE username = %s', ["super_admin", now_iso(), "aniket"])
            conn.commit()

    print(f"Imported {import_path} into Postgres.")
    print(json.dumps(counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
