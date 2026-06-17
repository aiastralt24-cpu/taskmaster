#!/usr/bin/env python3
import csv
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
PUBLIC = ROOT / "public"
DB_PATH = Path(os.environ.get("TASKMASTER_DB_PATH", ROOT / "data" / "taskmaster.sqlite3"))
SEED_PATH = ROOT / "seed" / "AstralVideoTracker.jsx"
APP_URL = os.environ.get("TASKMASTER_APP_URL", "http://127.0.0.1:3401")
SMTP_CONFIGURED = bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))

STATUSES = ["Concept Stage", "Scripting", "In Production", "In Review", "Ready", "Completed", "Published", "On Hold"]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]
BUCKET_DEFAULTS = {
    "Influencer & UGC Videos": {"bucketAdmin": "Aniket", "primaryOwner": "", "secondaryOwner": "", "reviewer": "Brand Review"},
    "NON-AI Product Video": {"bucketAdmin": "Jay", "primaryOwner": "", "secondaryOwner": "", "reviewer": "Brand Review"},
    "Project Case Study": {"bucketAdmin": "Jay", "primaryOwner": "Vaibhav", "secondaryOwner": "", "reviewer": "Project Review"},
    "Testimonial-Dealer": {"bucketAdmin": "Jay", "primaryOwner": "", "secondaryOwner": "", "reviewer": "Dealer Review"},
    "AI Generated Product Videos": {"bucketAdmin": "Aniket", "primaryOwner": "", "secondaryOwner": "", "reviewer": "Brand Review"},
    "AI Generated Infotainment Videos": {"bucketAdmin": "Aniket", "primaryOwner": "", "secondaryOwner": "", "reviewer": "Brand Review"},
    "": {"bucketAdmin": "Aniket", "primaryOwner": "", "secondaryOwner": "", "reviewer": "Brand Review"},
}
TASK_FIELDS = [
    "no",
    "brand",
    "bucket",
    "zone",
    "title",
    "length",
    "hook",
    "agency",
    "status",
    "owner",
    "bucketAdmin",
    "primaryOwner",
    "secondaryOwner",
    "reviewer",
    "deadline",
    "plannedStart",
    "publishDate",
    "actualCompletionDate",
    "delayReason",
    "assignmentStatus",
    "priority",
    "notes",
]
USER_ROLES = ["super_admin", "admin", "editor", "reviewer", "agency", "viewer"]
ASSET_TYPES = ["Script", "Raw Footage", "Edit Link", "Final Video", "Thumbnail", "Published URL", "Reference", "Other"]
CHECKLIST_STEPS = ["script", "shoot/design", "edit", "review", "publish"]
ACTIVE_STATUSES = ["Scripting", "In Production", "In Review", "Ready"]
DONE_STATUSES = ["Completed", "Published"]
STUCK_DAYS = 7
SESSION_COOKIE = "taskmaster_session"
SESSION_TTL_SECONDS = 14 * 86400
INITIAL_PASSWORD = "Taskmaster@2026"
SEEDED_USERS = [
    {"username": "jay", "displayName": "Jay", "role": "admin", "team": "Content", "access": [("bucket", "NON-AI Product Video"), ("bucket", "Project Case Study"), ("bucket", "Testimonial-Dealer")]},
    {"username": "yogen", "displayName": "Yogen", "role": "admin", "team": "Content", "access": []},
    {"username": "vaibhav", "displayName": "Vaibhav", "role": "editor", "team": "Production", "access": []},
    {"username": "aniket", "displayName": "Aniket", "role": "super_admin", "team": "Command", "access": []},
    {"username": "akash", "displayName": "Akash", "role": "editor", "team": "Production", "access": []},
    {"username": "arvind", "displayName": "Arvind", "role": "editor", "team": "Production", "access": []},
]


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password, stored):
    try:
        algorithm, salt, expected = stored.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hash_password(password, salt).split("$", 2)[2]
    return hmac.compare_digest(candidate, expected)


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY,
              no INTEGER NOT NULL,
              brand TEXT NOT NULL DEFAULT '',
              bucket TEXT NOT NULL DEFAULT '',
              zone TEXT NOT NULL DEFAULT '',
              title TEXT NOT NULL DEFAULT '',
              length TEXT DEFAULT '',
              hook TEXT DEFAULT '',
              agency TEXT DEFAULT '',
              status TEXT NOT NULL DEFAULT 'Concept Stage',
              owner TEXT DEFAULT '',
              bucketAdmin TEXT DEFAULT '',
              primaryOwner TEXT DEFAULT '',
              secondaryOwner TEXT DEFAULT '',
              reviewer TEXT DEFAULT '',
              deadline TEXT DEFAULT '',
              plannedStart TEXT DEFAULT '',
              publishDate TEXT DEFAULT '',
              actualCompletionDate TEXT DEFAULT '',
              delayReason TEXT DEFAULT '',
              assignmentStatus TEXT DEFAULT 'assigned',
              priority TEXT DEFAULT 'Medium',
              notes TEXT DEFAULT '',
              createdAt TEXT NOT NULL,
              updatedAt TEXT NOT NULL,
              completedAt TEXT DEFAULT '',
              lastStageChangedAt TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS activity_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              taskId TEXT NOT NULL,
              action TEXT NOT NULL,
              actorRole TEXT NOT NULL,
              changedAt TEXT NOT NULL,
              beforeJson TEXT DEFAULT '',
              afterJson TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              username TEXT NOT NULL UNIQUE,
              displayName TEXT NOT NULL,
              role TEXT NOT NULL,
              email TEXT DEFAULT '',
              phone TEXT DEFAULT '',
              team TEXT DEFAULT '',
              agencyName TEXT DEFAULT '',
              isAgencyUser INTEGER NOT NULL DEFAULT 0,
              notificationPrefs TEXT DEFAULT '{}',
              passwordHash TEXT NOT NULL,
              isActive INTEGER NOT NULL DEFAULT 1,
              mustChangePassword INTEGER NOT NULL DEFAULT 1,
              createdAt TEXT NOT NULL,
              updatedAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
              token TEXT PRIMARY KEY,
              userId TEXT NOT NULL,
              createdAt TEXT NOT NULL,
              expiresAt INTEGER NOT NULL,
              FOREIGN KEY(userId) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS user_access (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              userId TEXT NOT NULL,
              accessType TEXT NOT NULL,
              accessValue TEXT NOT NULL,
              UNIQUE(userId, accessType, accessValue)
            );
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
              token TEXT PRIMARY KEY,
              userId TEXT NOT NULL,
              createdAt TEXT NOT NULL,
              expiresAt INTEGER NOT NULL,
              usedAt TEXT DEFAULT '',
              FOREIGN KEY(userId) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS task_comments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              taskId TEXT NOT NULL,
              userId TEXT NOT NULL,
              body TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS task_assets (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              taskId TEXT NOT NULL,
              userId TEXT NOT NULL,
              assetType TEXT NOT NULL,
              label TEXT NOT NULL,
              url TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS approval_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              taskId TEXT NOT NULL,
              userId TEXT NOT NULL,
              decision TEXT NOT NULL,
              note TEXT DEFAULT '',
              createdAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notifications (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              userId TEXT NOT NULL,
              taskId TEXT DEFAULT '',
              title TEXT NOT NULL,
              body TEXT DEFAULT '',
              channel TEXT NOT NULL DEFAULT 'in_app',
              deliveryStatus TEXT NOT NULL DEFAULT 'queued',
              isRead INTEGER NOT NULL DEFAULT 0,
              createdAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS task_checklists (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              taskId TEXT NOT NULL,
              step TEXT NOT NULL,
              isDone INTEGER NOT NULL DEFAULT 0,
              updatedBy TEXT DEFAULT '',
              updatedAt TEXT NOT NULL,
              UNIQUE(taskId, step)
            );
            CREATE TABLE IF NOT EXISTS system_audit (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              actorUserId TEXT DEFAULT '',
              actorName TEXT DEFAULT '',
              action TEXT NOT NULL,
              subjectType TEXT DEFAULT '',
              subjectId TEXT DEFAULT '',
              metadataJson TEXT DEFAULT '',
              createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner);
            CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(userId);
            CREATE INDEX IF NOT EXISTS idx_comments_task ON task_comments(taskId);
            CREATE INDEX IF NOT EXISTS idx_assets_task ON task_assets(taskId);
            CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(userId, isRead);
            CREATE INDEX IF NOT EXISTS idx_audit_subject ON system_audit(subjectType, subjectId);
            CREATE INDEX IF NOT EXISTS idx_reset_user ON password_reset_tokens(userId, expiresAt);
            """
        )
        user_cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        user_new_cols = {
            "email": "TEXT DEFAULT ''",
            "phone": "TEXT DEFAULT ''",
            "team": "TEXT DEFAULT ''",
            "agencyName": "TEXT DEFAULT ''",
            "isAgencyUser": "INTEGER NOT NULL DEFAULT 0",
            "notificationPrefs": "TEXT DEFAULT '{}'",
        }
        for name, spec in user_new_cols.items():
            if name not in user_cols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {spec}")
        notification_cols = [r["name"] for r in conn.execute("PRAGMA table_info(notifications)").fetchall()]
        if "channel" not in notification_cols:
            conn.execute("ALTER TABLE notifications ADD COLUMN channel TEXT NOT NULL DEFAULT 'in_app'")
        if "deliveryStatus" not in notification_cols:
            conn.execute("ALTER TABLE notifications ADD COLUMN deliveryStatus TEXT NOT NULL DEFAULT 'queued'")
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()]
        new_cols = {
            "bucket": "TEXT NOT NULL DEFAULT ''",
            "bucketAdmin": "TEXT DEFAULT ''",
            "primaryOwner": "TEXT DEFAULT ''",
            "secondaryOwner": "TEXT DEFAULT ''",
            "reviewer": "TEXT DEFAULT ''",
            "plannedStart": "TEXT DEFAULT ''",
            "publishDate": "TEXT DEFAULT ''",
            "actualCompletionDate": "TEXT DEFAULT ''",
            "delayReason": "TEXT DEFAULT ''",
            "assignmentStatus": "TEXT DEFAULT 'assigned'",
        }
        for name, spec in new_cols.items():
            if name not in cols:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {name} {spec}")
        if "lastStageChangedAt" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN lastStageChangedAt TEXT DEFAULT ''")
            conn.execute("UPDATE tasks SET lastStageChangedAt = COALESCE(NULLIF(updatedAt, ''), createdAt)")
        conn.execute(
            """
            UPDATE tasks
            SET
              bucket = CASE WHEN bucket = '' OR bucket IS NULL THEN zone ELSE bucket END,
              primaryOwner = CASE WHEN primaryOwner = '' OR primaryOwner IS NULL THEN owner ELSE primaryOwner END
            """
        )
        for bucket, defaults in BUCKET_DEFAULTS.items():
            conn.execute(
                """
                UPDATE tasks
                SET
                  bucketAdmin = CASE WHEN bucketAdmin = '' OR bucketAdmin IS NULL THEN ? ELSE bucketAdmin END,
                  primaryOwner = CASE WHEN primaryOwner = '' OR primaryOwner IS NULL THEN ? ELSE primaryOwner END,
                  secondaryOwner = CASE WHEN secondaryOwner = '' OR secondaryOwner IS NULL THEN ? ELSE secondaryOwner END,
                  reviewer = CASE WHEN reviewer = '' OR reviewer IS NULL THEN ? ELSE reviewer END
                WHERE bucket = ?
                """,
                [defaults["bucketAdmin"], defaults["primaryOwner"], defaults["secondaryOwner"], defaults["reviewer"], bucket],
            )
        count = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
        if count == 0:
            seed_tasks(conn)
        seed_users(conn)


def parse_seed():
    text = SEED_PATH.read_text(encoding="utf-8")
    match = re.search(r"const SEED = (\[[\s\S]*?\]);;", text)
    if not match:
        raise RuntimeError("Could not find SEED array in seed/AstralVideoTracker.jsx")
    return json.loads(match.group(1))


def normalize_task(row, existing=None):
    ts = now_iso()
    bucket = str(row.get("bucket") or row.get("zone") or "")
    defaults = BUCKET_DEFAULTS.get(bucket, {"bucketAdmin": "", "primaryOwner": "", "secondaryOwner": "", "reviewer": ""})
    status = row.get("status") or "Concept Stage"
    if status not in STATUSES:
        status = "Concept Stage"
    priority = row.get("priority") or "Medium"
    if priority not in PRIORITIES:
        priority = "Medium"
    completed = row.get("completedAt") or ""
    if status in DONE_STATUSES and not completed:
        completed = ts
    if status not in DONE_STATUSES:
        completed = ""
    previous_status = existing["status"] if existing else row.get("status")
    stage_changed = row.get("lastStageChangedAt") or (existing["lastStageChangedAt"] if existing and "lastStageChangedAt" in existing.keys() else "")
    if not stage_changed or (existing and previous_status != status):
        stage_changed = ts
    base = {
        "id": row.get("id") or f"task_{int(time.time() * 1000)}_{os.urandom(3).hex()}",
        "no": int(row.get("no") or 0),
        "brand": str(row.get("brand") or ""),
        "bucket": bucket,
        "zone": str(row.get("zone") or ""),
        "title": str(row.get("title") or ""),
        "length": str(row.get("length") or ""),
        "hook": str(row.get("hook") or ""),
        "agency": str(row.get("agency") or ""),
        "status": status,
        "owner": str(row.get("owner") or ""),
        "bucketAdmin": str(row.get("bucketAdmin") or defaults["bucketAdmin"]),
        "primaryOwner": str(row.get("primaryOwner") or row.get("owner") or defaults["primaryOwner"]),
        "secondaryOwner": str(row.get("secondaryOwner") or defaults["secondaryOwner"]),
        "reviewer": str(row.get("reviewer") or defaults["reviewer"]),
        "deadline": str(row.get("deadline") or ""),
        "plannedStart": str(row.get("plannedStart") or ""),
        "publishDate": str(row.get("publishDate") or ""),
        "actualCompletionDate": str(row.get("actualCompletionDate") or ""),
        "delayReason": str(row.get("delayReason") or ""),
        "assignmentStatus": str(row.get("assignmentStatus") or "assigned"),
        "priority": priority,
        "notes": str(row.get("notes") or ""),
        "createdAt": row.get("createdAt") or (existing["createdAt"] if existing else ts),
        "updatedAt": ts,
        "completedAt": completed,
        "lastStageChangedAt": stage_changed,
    }
    if base["no"] <= 0:
        base["no"] = next_no()
    return base


def seed_tasks(conn):
    ts = now_iso()
    rows = []
    for item in parse_seed():
        item["id"] = f"seed_{int(item.get('no') or 0):03d}"
        item["priority"] = "Medium"
        item["notes"] = ""
        item["createdAt"] = ts
        item["updatedAt"] = ts
        item["completedAt"] = ts if item.get("status") in DONE_STATUSES else ""
        item["lastStageChangedAt"] = ts
        rows.append(normalize_task(item))
    insert_many(conn, rows)


def seed_users(conn):
    ts = now_iso()
    for user in SEEDED_USERS:
        existing = conn.execute("SELECT * FROM users WHERE username = ?", [user["username"]]).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE users
                SET displayName = ?, role = ?, team = CASE WHEN team = '' OR team IS NULL THEN ? ELSE team END, isActive = 1, updatedAt = ?
                WHERE username = ?
                """,
                [user["displayName"], user["role"], user.get("team", ""), ts, user["username"]],
            )
        else:
            conn.execute(
                """
                INSERT INTO users(id, username, displayName, role, email, phone, team, agencyName, isAgencyUser, notificationPrefs, passwordHash, isActive, mustChangePassword, createdAt, updatedAt)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    f"user_{user['username']}",
                    user["username"],
                    user["displayName"],
                    user["role"],
                    user.get("email", ""),
                    user.get("phone", ""),
                    user.get("team", ""),
                    user.get("agencyName", ""),
                    1 if user.get("role") == "agency" else 0,
                    "{}",
                    hash_password(INITIAL_PASSWORD),
                    1,
                    1,
                    ts,
                    ts,
                ],
            )
        user_id = f"user_{user['username']}"
        for access_type, access_value in user.get("access", []):
            conn.execute(
                "INSERT OR IGNORE INTO user_access(userId, accessType, accessValue) VALUES(?,?,?)",
                [user_id, access_type, access_value],
            )
    conn.execute("UPDATE users SET role = 'admin' WHERE role = 'super_admin' AND username != 'aniket'")
    conn.execute("UPDATE users SET role = 'super_admin', isActive = 1, updatedAt = ? WHERE username = 'aniket'", [ts])


def public_user(row):
    if not row:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "displayName": row["displayName"],
        "role": row["role"],
        "email": row["email"] if "email" in row.keys() else "",
        "phone": row["phone"] if "phone" in row.keys() else "",
        "team": row["team"] if "team" in row.keys() else "",
        "agencyName": row["agencyName"] if "agencyName" in row.keys() else "",
        "isAgencyUser": bool(row["isAgencyUser"]) if "isAgencyUser" in row.keys() else False,
        "notificationPrefs": safe_json(row["notificationPrefs"] if "notificationPrefs" in row.keys() else "{}", {}),
        "isActive": bool(row["isActive"]),
        "mustChangePassword": bool(row["mustChangePassword"]),
    }


def safe_json(value, fallback):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def all_users(conn):
    rows = conn.execute("SELECT * FROM users ORDER BY role = 'super_admin' DESC, displayName").fetchall()
    users = []
    for row in rows:
        item = public_user(row)
        access = conn.execute("SELECT accessType, accessValue FROM user_access WHERE userId = ? ORDER BY accessType, accessValue", [row["id"]]).fetchall()
        item["access"] = [dict(a) for a in access]
        users.append(item)
    return users


def user_by_name(conn, name):
    if not name:
        return None
    return conn.execute(
        "SELECT * FROM users WHERE LOWER(displayName) = LOWER(?) OR LOWER(username) = LOWER(?) LIMIT 1",
        [name, name],
    ).fetchone()


def notify_user(conn, user_id, task_id, title, body=""):
    if not user_id:
        return
    conn.execute(
        "INSERT INTO notifications(userId,taskId,title,body,channel,deliveryStatus,isRead,createdAt) VALUES(?,?,?,?,?,?,0,?)",
        [user_id, task_id or "", title, body, "in_app", "queued", now_iso()],
    )


def audit_event(conn, actor=None, action="", subject_type="", subject_id="", metadata=None):
    actor = actor or {}
    conn.execute(
        "INSERT INTO system_audit(actorUserId,actorName,action,subjectType,subjectId,metadataJson,createdAt) VALUES(?,?,?,?,?,?,?)",
        [
            actor.get("id", ""),
            actor.get("displayName", ""),
            action,
            subject_type,
            subject_id,
            json.dumps(metadata or {}),
            now_iso(),
        ],
    )


def user_access_values(conn, user_id, access_type):
    rows = conn.execute("SELECT accessValue FROM user_access WHERE userId = ? AND accessType = ?", [user_id, access_type]).fetchall()
    return [r["accessValue"] for r in rows]


def canonical_person_name(conn, value):
    row = user_by_name(conn, value)
    return row["displayName"] if row else str(value or "").strip()


def canonicalize_task_people(conn, payload):
    for field in ["owner", "bucketAdmin", "primaryOwner", "secondaryOwner", "reviewer"]:
        if field in payload and payload.get(field):
            payload[field] = canonical_person_name(conn, payload.get(field))
    return payload


def username_available(conn, username, user_id=""):
    row = conn.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", [username]).fetchone()
    return not row or row["id"] == user_id


def display_name_available(conn, display_name, user_id=""):
    row = conn.execute("SELECT id FROM users WHERE LOWER(displayName) = LOWER(?)", [display_name]).fetchone()
    return not row or row["id"] == user_id


def task_exists(conn, task_id):
    return conn.execute("SELECT 1 FROM tasks WHERE id = ? LIMIT 1", [task_id]).fetchone() is not None


def task_collaboration(conn, task_id):
    ensure_task_checklist(conn, task_id)
    comments = conn.execute(
        """
        SELECT task_comments.*, users.displayName, users.username
        FROM task_comments JOIN users ON users.id = task_comments.userId
        WHERE taskId = ? ORDER BY task_comments.id DESC LIMIT 50
        """,
        [task_id],
    ).fetchall()
    assets = conn.execute(
        """
        SELECT task_assets.*, users.displayName, users.username
        FROM task_assets JOIN users ON users.id = task_assets.userId
        WHERE taskId = ? ORDER BY task_assets.id DESC LIMIT 50
        """,
        [task_id],
    ).fetchall()
    approvals = conn.execute(
        """
        SELECT approval_events.*, users.displayName, users.username
        FROM approval_events JOIN users ON users.id = approval_events.userId
        WHERE taskId = ? ORDER BY approval_events.id DESC LIMIT 30
        """,
        [task_id],
    ).fetchall()
    checklist = conn.execute(
        "SELECT * FROM task_checklists WHERE taskId = ? ORDER BY id",
        [task_id],
    ).fetchall()
    activity = conn.execute(
        "SELECT * FROM activity_log WHERE taskId = ? ORDER BY id DESC LIMIT 20",
        [task_id],
    ).fetchall()
    return {
        "comments": [dict(r) for r in comments],
        "assets": [dict(r) for r in assets],
        "approvals": [dict(r) for r in approvals],
        "checklist": [dict(r) for r in checklist],
        "activity": [dict(r) for r in activity],
    }


def ensure_task_checklist(conn, task_id):
    ts = now_iso()
    for step in CHECKLIST_STEPS:
        conn.execute(
            "INSERT OR IGNORE INTO task_checklists(taskId, step, isDone, updatedBy, updatedAt) VALUES(?,?,?,?,?)",
            [task_id, step, 0, "", ts],
        )


def task_to_dict(row):
    task = {k: row[k] for k in row.keys()}
    return enrich_task(task)


def enrich_task(task):
    task["risk"] = task_risk(task)
    return task


def insert_many(conn, rows):
    conn.executemany(
        """
        INSERT INTO tasks
        (id,no,brand,bucket,zone,title,length,hook,agency,status,owner,bucketAdmin,primaryOwner,secondaryOwner,reviewer,deadline,plannedStart,publishDate,actualCompletionDate,delayReason,assignmentStatus,priority,notes,createdAt,updatedAt,completedAt,lastStageChangedAt)
        VALUES
        (:id,:no,:brand,:bucket,:zone,:title,:length,:hook,:agency,:status,:owner,:bucketAdmin,:primaryOwner,:secondaryOwner,:reviewer,:deadline,:plannedStart,:publishDate,:actualCompletionDate,:delayReason,:assignmentStatus,:priority,:notes,:createdAt,:updatedAt,:completedAt,:lastStageChangedAt)
        """,
        rows,
    )


def next_no():
    with connect() as conn:
        row = conn.execute("SELECT COALESCE(MAX(no), 0) + 1 AS n FROM tasks").fetchone()
        return int(row["n"])


def filters_from_query(query):
    clauses = []
    params = []
    exacts = {
        "brand": "brand",
        "bucket": "bucket",
        "zone": "zone",
        "agency": "agency",
        "status": "status",
        "owner": "owner",
        "bucketAdmin": "bucketAdmin",
        "primaryOwner": "primaryOwner",
        "secondaryOwner": "secondaryOwner",
        "reviewer": "reviewer",
        "priority": "priority",
    }
    for qk, col in exacts.items():
        val = query.get(qk, [""])[0]
        if val and val != "All":
            clauses.append(f"{col} = ?")
            params.append(val)
    q = query.get("q", [""])[0].strip().lower()
    if q:
        clauses.append("(LOWER(title) LIKE ? OR LOWER(hook) LIKE ? OR LOWER(owner) LIKE ? OR LOWER(zone) LIKE ? OR LOWER(agency) LIKE ?)")
        params.extend([f"%{q}%"] * 5)
    start = query.get("deadlineFrom", [""])[0]
    end = query.get("deadlineTo", [""])[0]
    if start:
        clauses.append("deadline >= ?")
        params.append(start)
    if end:
        clauses.append("deadline <= ?")
        params.append(end)
    overdue = query.get("overdue", [""])[0]
    today = time.strftime("%Y-%m-%d")
    if overdue == "overdue":
        clauses.append("deadline != '' AND deadline < ? AND status NOT IN ('Completed','Published')")
        params.append(today)
    elif overdue == "no-deadline":
        clauses.append("(deadline = '' OR deadline IS NULL)")
    quick = query.get("quickFilter", [""])[0]
    if quick == "needs-owner":
        clauses.append("(primaryOwner = '' OR primaryOwner IS NULL)")
    elif quick == "needs-secondary":
        clauses.append("(secondaryOwner = '' OR secondaryOwner IS NULL)")
    elif quick == "needs-admin":
        clauses.append("(bucketAdmin = '' OR bucketAdmin IS NULL)")
    elif quick == "needs-deadline":
        clauses.append("(deadline = '' OR deadline IS NULL)")
    elif quick == "stuck-review":
        cutoff = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - STUCK_DAYS * 86400))
        clauses.append("status = 'In Review' AND COALESCE(NULLIF(lastStageChangedAt, ''), updatedAt) <= ?")
        params.append(cutoff)
    elif quick == "ready-to-publish":
        clauses.append("status IN ('Ready','Completed')")
    elif quick == "in-review":
        clauses.append("status = 'In Review'")
    elif quick == "active":
        clauses.append("status IN ('Scripting','In Production','In Review','Ready')")
    elif quick == "completed":
        clauses.append("status = 'Completed'")
    elif quick == "published":
        clauses.append("status = 'Published'")
    elif quick == "recent":
        cutoff = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 7 * 86400))
        clauses.append("updatedAt >= ?")
        params.append(cutoff)
    return clauses, params


def visibility_filter_for_user(user):
    if not user:
        return "1 = 0", []
    role = role_from_user(user)
    if role == "super_admin":
        return "", []
    with connect() as conn:
        buckets = user_access_values(conn, user["id"], "bucket")
        agencies = user_access_values(conn, user["id"], "agency")
    if role == "admin" and (buckets or agencies):
        predicates = []
        params = []
        if buckets:
            predicates.append(f"bucket IN ({','.join(['?'] * len(buckets))})")
            params.extend(buckets)
        if agencies:
            predicates.append(f"agency IN ({','.join(['?'] * len(agencies))})")
            params.extend(agencies)
        return "(" + " OR ".join(predicates) + ")", params
    if role == "agency":
        agency_values = [user.get("agencyName") or "", *agencies]
        agency_values = [a for a in dict.fromkeys(agency_values) if a]
        if agency_values:
            return f"agency IN ({','.join(['?'] * len(agency_values))})", agency_values
    names = {str(user.get("displayName") or "").strip().lower(), str(user.get("username") or "").strip().lower()}
    names = [n for n in names if n]
    if not names:
        return "1 = 0", []
    fields = ["owner", "bucketAdmin", "primaryOwner", "secondaryOwner", "reviewer", "agency"]
    predicates = []
    params = []
    for field in fields:
        predicates.append(f"LOWER({field}) IN ({','.join(['?'] * len(names))})")
        params.extend(names)
    return "(" + " OR ".join(predicates) + ")", params


def can_access_task(conn, user, task_id):
    if not user:
        return False
    if role_from_user(user) == "super_admin":
        return task_exists(conn, task_id)
    clause, params = visibility_filter_for_user(user)
    if not clause:
        return task_exists(conn, task_id)
    row = conn.execute(f"SELECT 1 FROM tasks WHERE id = ? AND {clause} LIMIT 1", [task_id, *params]).fetchone()
    return row is not None


def query_tasks(query, user=None):
    clauses, params = filters_from_query(query)
    visibility_clause, visibility_params = visibility_filter_for_user(user)
    if visibility_clause:
        clauses.append(visibility_clause)
        params.extend(visibility_params)
    sql = "SELECT * FROM tasks"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY CASE WHEN deadline = '' THEN 1 ELSE 0 END, deadline ASC, no ASC"
    with connect() as conn:
        return [redact_task_for_user(task_to_dict(r), user) for r in conn.execute(sql, params).fetchall()]


def redact_task_for_user(task, user):
    if not user or role_from_user(user) != "agency":
        return task
    safe = dict(task)
    safe["notes"] = ""
    safe["hook"] = ""
    safe["bucketAdmin"] = ""
    safe["reviewer"] = safe.get("reviewer") if safe.get("reviewer") in [user.get("displayName"), user.get("username")] else ""
    safe["owner"] = safe.get("primaryOwner") or safe.get("owner") or ""
    return safe


def days_since(iso_value):
    if not iso_value:
        return 0
    try:
        then = time.mktime(time.strptime(iso_value[:19] + "Z", "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return 0
    return max(0, int((time.time() - then) // 86400))


def task_risk(t):
    today = time.strftime("%Y-%m-%d")
    end_week = time.strftime("%Y-%m-%d", time.localtime(time.time() + 6 * 86400))
    stage_age = days_since(t.get("lastStageChangedAt") or t.get("updatedAt") or t.get("createdAt"))
    deadline = t.get("deadline") or ""
    status = t.get("status") or "Concept Stage"
    return {
        "missingOwner": not bool(t.get("primaryOwner") or t.get("owner")),
        "missingPrimary": not bool(t.get("primaryOwner") or t.get("owner")),
        "missingSecondary": not bool(t.get("secondaryOwner")),
        "missingAdmin": not bool(t.get("bucketAdmin")),
        "missingDeadline": not bool(deadline),
        "overdue": bool(deadline and deadline < today and status not in DONE_STATUSES),
        "dueSoon": bool(deadline and today <= deadline <= end_week and status not in DONE_STATUSES),
        "stuck": bool(status == "In Review" and stage_age >= STUCK_DAYS),
        "readyToPublish": status in ["Ready", "Completed"],
        "stageAgeDays": stage_age,
    }


def raw_tasks(query=None, user=None):
    query = query or {}
    clauses, params = filters_from_query(query)
    visibility_clause, visibility_params = visibility_filter_for_user(user)
    if visibility_clause:
        clauses.append(visibility_clause)
        params.extend(visibility_params)
    sql = "SELECT * FROM tasks"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY CASE WHEN deadline = '' THEN 1 ELSE 0 END, deadline ASC, no ASC"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def analytics_for(tasks):
    today = time.strftime("%Y-%m-%d")
    end_week = time.strftime("%Y-%m-%d", time.localtime(time.time() + 6 * 86400))
    cards = {
        "total": len(tasks),
        "inPipeline": sum(1 for t in tasks if t["status"] in ACTIVE_STATUSES),
        "published": sum(1 for t in tasks if t["status"] == "Published"),
        "completed": sum(1 for t in tasks if t["status"] == "Completed"),
        "overdue": sum(1 for t in tasks if t["deadline"] and t["deadline"] < today and t["status"] not in DONE_STATUSES),
        "dueThisWeek": sum(1 for t in tasks if t["deadline"] and today <= t["deadline"] <= end_week and t["status"] not in DONE_STATUSES),
        "unassigned": sum(1 for t in tasks if not (t.get("primaryOwner") or t.get("owner"))),
    }

    owner_status = {}
    owner_overdue = {}
    status_counts = {s: 0 for s in STATUSES}
    agency_load = {}
    risk = {"Overdue": 0, "Due today": 0, "Due this week": 0, "No deadline": 0, "Later": 0}
    weeks = {}
    heatmap = {}
    planned_completed = {}
    review_aging = {"0-2 days": 0, "3-6 days": 0, "7+ days": 0}
    agency_throughput = {}

    for t in tasks:
        owner = t.get("primaryOwner") or t.get("owner") or "Unassigned"
        agency = t["agency"] or "Unassigned"
        status = t["status"]
        owner_status.setdefault(owner, {s: 0 for s in STATUSES})
        owner_status[owner][status] = owner_status[owner].get(status, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
        agency_load[agency] = agency_load.get(agency, 0) + 1

        deadline = t["deadline"]
        if deadline and deadline < today and status not in DONE_STATUSES:
            owner_overdue[owner] = owner_overdue.get(owner, 0) + 1
            risk["Overdue"] += 1
        elif deadline == today and status not in DONE_STATUSES:
            risk["Due today"] += 1
        elif deadline and today < deadline <= end_week and status not in DONE_STATUSES:
            risk["Due this week"] += 1
        elif not deadline:
            risk["No deadline"] += 1
        elif status not in DONE_STATUSES:
            risk["Later"] += 1

        if deadline:
            y, m, d = [int(x) for x in deadline.split("-")]
            week_key = time.strftime("%Y-W%W", time.strptime(f"{y}-{m}-{d}", "%Y-%m-%d"))
            weeks[week_key] = weeks.get(week_key, 0) + 1
            bucket = t.get("bucket") or t.get("zone") or "Unassigned"
            heatmap.setdefault(week_key, {})
            heatmap[week_key][bucket] = heatmap[week_key].get(bucket, 0) + 1

        if status == "In Review":
            age = t.get("risk", {}).get("stageAgeDays", 0)
            if age <= 2:
                review_aging["0-2 days"] += 1
            elif age <= 6:
                review_aging["3-6 days"] += 1
            else:
                review_aging["7+ days"] += 1

        month_key = (t.get("deadline") or t.get("completedAt") or t.get("updatedAt") or "")[:7] or "No date"
        planned_completed.setdefault(month_key, {"period": month_key, "planned": 0, "completed": 0, "published": 0})
        if t.get("deadline"):
            planned_completed[month_key]["planned"] += 1
        if status == "Completed":
            planned_completed[month_key]["completed"] += 1
        if status == "Published":
            planned_completed[month_key]["published"] += 1

        agency_throughput.setdefault(agency, {"agency": agency, "active": 0, "completed": 0, "published": 0, "stuck": 0})
        agency_throughput[agency]["active"] += 1 if status in ACTIVE_STATUSES else 0
        agency_throughput[agency]["completed"] += 1 if status == "Completed" else 0
        agency_throughput[agency]["published"] += 1 if status == "Published" else 0
        agency_throughput[agency]["stuck"] += 1 if t.get("risk", {}).get("stuck") else 0

    funnel = [{"status": status, "count": status_counts.get(status, 0)} for status in STATUSES]
    deadline_heatmap = []
    for week, buckets in sorted(heatmap.items())[:12]:
        for bucket, count in sorted(buckets.items()):
            deadline_heatmap.append({"week": week, "bucket": bucket, "count": count})

    return {
        "cards": cards,
        "ownerWorkload": [{"owner": k, **v, "total": sum(v.values())} for k, v in sorted(owner_status.items(), key=lambda kv: -sum(kv[1].values()))],
        "ownerOverdue": [{"owner": k, "count": v} for k, v in sorted(owner_overdue.items(), key=lambda kv: -kv[1])],
        "upcomingWeeks": [{"week": k, "count": v} for k, v in sorted(weeks.items())[:10]],
        "deadlineRisk": [{"name": k, "count": v} for k, v in risk.items()],
        "statusDistribution": [{"status": k, "count": v} for k, v in status_counts.items()],
        "agencyLoad": [{"agency": k, "count": v} for k, v in sorted(agency_load.items(), key=lambda kv: -kv[1])],
        "productionFunnel": funnel,
        "deadlineHeatmap": deadline_heatmap,
        "reviewAging": [{"bucket": k, "count": v} for k, v in review_aging.items()],
        "agencyThroughput": sorted(agency_throughput.values(), key=lambda r: (-(r["active"] + r["completed"] + r["published"]), r["agency"])),
        "plannedVsCompleted": [planned_completed[k] for k in sorted(planned_completed) if k != "No date"][-8:],
    }


def group_count(tasks, *keys, risk_key=None, status_filter=None):
    grouped = {}
    for t in tasks:
        if status_filter and t["status"] not in status_filter:
            continue
        if risk_key and not t["risk"].get(risk_key):
            continue
        label = " / ".join((t.get(k) or "Unassigned") for k in keys)
        grouped[label] = grouped.get(label, 0) + 1
    return [{"name": k, "count": v} for k, v in sorted(grouped.items(), key=lambda kv: -kv[1])]


def command_center_for(tasks):
    risks = [t["risk"] for t in tasks]
    cards = {
        "needsAttention": sum(1 for r in risks if r["missingPrimary"] or r["missingSecondary"] or r["missingAdmin"] or r["missingDeadline"] or r["overdue"] or r["stuck"] or r["readyToPublish"]),
        "missingOwner": sum(1 for r in risks if r["missingOwner"]),
        "missingPrimary": sum(1 for r in risks if r["missingPrimary"]),
        "missingSecondary": sum(1 for r in risks if r["missingSecondary"]),
        "missingAdmin": sum(1 for r in risks if r["missingAdmin"]),
        "missingDeadline": sum(1 for r in risks if r["missingDeadline"]),
        "stuckReview": sum(1 for r in risks if r["stuck"]),
        "readyToPublish": sum(1 for r in risks if r["readyToPublish"]),
        "recentlyChanged": sum(1 for t in tasks if days_since(t.get("updatedAt")) <= 7),
    }
    published_week = sum(1 for t in tasks if t["status"] == "Published" and days_since(t.get("completedAt")) <= 7)
    published_month = sum(1 for t in tasks if t["status"] == "Published" and days_since(t.get("completedAt")) <= 30)
    completed_week = sum(1 for t in tasks if t["status"] == "Completed" and days_since(t.get("completedAt")) <= 7)
    completed_month = sum(1 for t in tasks if t["status"] == "Completed" and days_since(t.get("completedAt")) <= 30)
    insights = [
        {"title": f"{cards['missingPrimary']} tasks need primary owners", "body": "Primary owner is the directly accountable person for each content item.", "quickFilter": "needs-owner", "tone": "red" if cards["missingPrimary"] else "green"},
        {"title": f"{cards['missingSecondary']} tasks need secondary owners", "body": "Secondary owners keep work moving when the primary person is blocked.", "quickFilter": "needs-secondary", "tone": "amber" if cards["missingSecondary"] else "green"},
        {"title": f"{cards['missingDeadline']} tasks need deadlines", "body": "Deadline analytics become meaningful once this hygiene pass is complete.", "quickFilter": "needs-deadline", "tone": "amber" if cards["missingDeadline"] else "green"},
        {"title": f"{sum(1 for t in tasks if t['status'] == 'In Review')} items are waiting in review", "body": "Review is the highest-friction stage to watch this week.", "quickFilter": "in-review", "tone": "amber"},
    ]
    owner_scorecards = []
    by_owner = {}
    for t in tasks:
        owner = t.get("primaryOwner") or t.get("owner") or "Unassigned"
        by_owner.setdefault(owner, {"owner": owner, "active": 0, "blocked": 0, "complete": 0, "total": 0})
        by_owner[owner]["total"] += 1
        by_owner[owner]["active"] += 1 if t["status"] in ACTIVE_STATUSES else 0
        by_owner[owner]["blocked"] += 1 if t["risk"]["missingDeadline"] or t["risk"]["missingOwner"] or t["risk"]["stuck"] or t["risk"]["overdue"] else 0
        by_owner[owner]["complete"] += 1 if t["status"] in DONE_STATUSES else 0
    owner_scorecards = sorted(by_owner.values(), key=lambda x: (-x["blocked"], -x["active"], -x["total"]))[:8]
    agency_health = []
    by_agency = {}
    for t in tasks:
        agency = t["agency"] or "Unassigned"
        by_agency.setdefault(agency, {"agency": agency, "active": 0, "stuck": 0, "missingOwner": 0, "total": 0})
        by_agency[agency]["total"] += 1
        by_agency[agency]["active"] += 1 if t["status"] in ACTIVE_STATUSES else 0
        by_agency[agency]["stuck"] += 1 if t["risk"]["stuck"] else 0
        by_agency[agency]["missingOwner"] += 1 if t["risk"]["missingOwner"] else 0
    agency_health = sorted(by_agency.values(), key=lambda x: (-x["active"], -x["total"]))
    by_bucket = {}
    for t in tasks:
        bucket = t.get("bucket") or t.get("zone") or "Unassigned"
        by_bucket.setdefault(bucket, {"bucket": bucket, "admin": t.get("bucketAdmin") or "Unassigned", "total": 0, "active": 0, "missingPrimary": 0, "missingSecondary": 0, "missingDeadline": 0, "ready": 0})
        by_bucket[bucket]["total"] += 1
        by_bucket[bucket]["active"] += 1 if t["status"] in ACTIVE_STATUSES else 0
        by_bucket[bucket]["missingPrimary"] += 1 if t["risk"]["missingPrimary"] else 0
        by_bucket[bucket]["missingSecondary"] += 1 if t["risk"]["missingSecondary"] else 0
        by_bucket[bucket]["missingDeadline"] += 1 if t["risk"]["missingDeadline"] else 0
        by_bucket[bucket]["ready"] += 1 if t["status"] in ["Ready", "Completed"] else 0
    bucket_health = sorted(by_bucket.values(), key=lambda x: (-x["missingPrimary"] - x["missingSecondary"] - x["missingDeadline"], -x["total"]))
    by_admin = {}
    for t in tasks:
        admin = t.get("bucketAdmin") or "Unassigned"
        by_admin.setdefault(admin, {"admin": admin, "buckets": set(), "total": 0, "needsAttention": 0, "active": 0})
        by_admin[admin]["buckets"].add(t.get("bucket") or t.get("zone") or "Unassigned")
        by_admin[admin]["total"] += 1
        by_admin[admin]["active"] += 1 if t["status"] in ACTIVE_STATUSES else 0
        by_admin[admin]["needsAttention"] += 1 if t["risk"]["missingPrimary"] or t["risk"]["missingSecondary"] or t["risk"]["missingDeadline"] or t["risk"]["stuck"] else 0
    admin_health = []
    for v in by_admin.values():
        admin_health.append({**v, "bucketCount": len(v["buckets"]), "buckets": sorted(v["buckets"])})
    admin_health = sorted(admin_health, key=lambda x: (-x["needsAttention"], -x["active"], -x["total"]))
    return {
        "cards": cards,
        "insights": insights,
        "missingOwnerByZone": group_count(tasks, "bucket", risk_key="missingPrimary")[:8],
        "missingSecondaryByBucket": group_count(tasks, "bucket", risk_key="missingSecondary")[:8],
        "missingDeadlineByStatus": group_count(tasks, "status", risk_key="missingDeadline")[:8],
        "reviewBottlenecks": [t for t in tasks if t["status"] == "In Review"][:10],
        "readyToPublish": [t for t in tasks if t["status"] in ["Ready", "Completed"]][:10],
        "ownerScorecards": owner_scorecards,
        "agencyHealth": agency_health,
        "bucketHealth": bucket_health,
        "adminHealth": admin_health,
        "published": {"week": published_week, "month": published_month},
        "completed": {"week": completed_week, "month": completed_month},
    }


def access_matrix(conn):
    users = all_users(conn)
    rows = []
    for user in users:
        visible = query_tasks({}, user)
        access = user.get("access", [])
        rows.append({
            "user": user,
            "visibleTasks": len(visible),
            "canCreate": can_write(user["role"]),
            "canEdit": can_write(user["role"]),
            "canReview": user["role"] in ["super_admin", "admin", "editor", "reviewer"],
            "canImport": can_admin(user["role"]),
            "canDelete": can_admin(user["role"]),
            "canManageUsers": can_admin(user["role"]),
            "scope": access or ([{"accessType": "agency", "accessValue": user.get("agencyName")}] if user.get("agencyName") else [{"accessType": "assigned", "accessValue": user["displayName"]}]),
        })
    return rows


def digest_for_user(conn, user):
    tasks = query_tasks({}, user)
    today = time.strftime("%Y-%m-%d")
    end_week = time.strftime("%Y-%m-%d", time.localtime(time.time() + 6 * 86400))
    due_today = [t for t in tasks if t.get("deadline") == today and t.get("status") not in DONE_STATUSES]
    due_soon = [t for t in tasks if t.get("deadline") and today < t["deadline"] <= end_week and t.get("status") not in DONE_STATUSES]
    overdue = [t for t in tasks if t.get("deadline") and t["deadline"] < today and t.get("status") not in DONE_STATUSES]
    review = [t for t in tasks if t.get("status") == "In Review"]
    ready = [t for t in tasks if t.get("status") in ["Ready", "Completed"]]
    blocked = [t for t in tasks if t.get("risk", {}).get("missingDeadline") or t.get("risk", {}).get("stuck") or t.get("risk", {}).get("overdue")]
    return {
        "dueToday": due_today[:20],
        "dueSoon": due_soon[:20],
        "overdue": overdue[:20],
        "waitingForReview": review[:20],
        "readyToPublish": ready[:20],
        "blocked": blocked[:20],
        "summary": {
            "dueToday": len(due_today),
            "dueSoon": len(due_soon),
            "overdue": len(overdue),
            "waitingForReview": len(review),
            "readyToPublish": len(ready),
            "blocked": len(blocked),
        },
    }


def deployment_status():
    return {
        "appUrl": APP_URL,
        "databasePath": str(DB_PATH),
        "smtpConfigured": SMTP_CONFIGURED,
        "httpsReady": APP_URL.startswith("https://"),
        "backupScript": "scripts/backup_taskmaster.sh",
        "migrationStyle": "additive init_db migrations",
        "checks": [
            {"label": "HTTPS/domain configured", "ok": APP_URL.startswith("https://")},
            {"label": "Email provider configured", "ok": SMTP_CONFIGURED},
            {"label": "SQLite database path set", "ok": bool(DB_PATH)},
            {"label": "Aniket single super admin enforced", "ok": True},
        ],
    }


def role_from_user(user):
    return user.get("role") if user else "viewer"


def can_write(role):
    return role in ["super_admin", "admin", "editor"]


def can_collaborate(role):
    return role in ["super_admin", "admin", "editor", "reviewer", "agency"]


def can_review(role):
    return role in ["super_admin", "admin", "editor", "reviewer"]


def can_admin(role):
    return role == "super_admin"


def can_super_admin(role):
    return role == "super_admin"


def action_label(before, after, bulk=False):
    prefix = "bulk " if bulk else ""
    if before.get("status") != after.get("status"):
        if after.get("status") == "Published":
            return prefix + "task published"
        if after.get("status") == "Completed":
            return prefix + "task completed"
        return prefix + "status changed"
    if before.get("owner") != after.get("owner"):
        return prefix + ("owner assigned" if after.get("owner") else "owner cleared")
    if before.get("primaryOwner") != after.get("primaryOwner"):
        return prefix + ("primary owner assigned" if after.get("primaryOwner") else "primary owner cleared")
    if before.get("secondaryOwner") != after.get("secondaryOwner"):
        return prefix + ("secondary owner assigned" if after.get("secondaryOwner") else "secondary owner cleared")
    if before.get("bucketAdmin") != after.get("bucketAdmin"):
        return prefix + "bucket admin changed"
    if before.get("bucket") != after.get("bucket"):
        return prefix + "bucket changed"
    if before.get("deadline") != after.get("deadline"):
        return prefix + "deadline changed"
    if before.get("priority") != after.get("priority"):
        return prefix + "priority changed"
    return prefix + "task updated"


class Handler(BaseHTTPRequestHandler):
    server_version = "Taskmaster/1.0"

    def log_message(self, fmt, *args):
        return

    def send_json(self, value, status=200, headers=None):
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, val in (headers or {}).items():
            self.send_header(key, val)
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def cookie_value(self, name):
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            if "=" not in part:
                continue
            key, val = part.strip().split("=", 1)
            if key == name:
                return urllib.parse.unquote(val)
        return ""

    def current_user(self):
        token = self.cookie_value(SESSION_COOKIE)
        if not token:
            return None
        now = int(time.time())
        with connect() as conn:
            row = conn.execute(
                """
                SELECT users.* FROM sessions
                JOIN users ON users.id = sessions.userId
                WHERE sessions.token = ? AND sessions.expiresAt > ? AND users.isActive = 1
                """,
                [token, now],
            ).fetchone()
        return public_user(row)

    def require_user(self):
        user = self.current_user()
        if not user:
            self.send_json({"error": "Login required."}, 401)
            return None
        return user

    def login(self):
        payload = self.read_json()
        username = str(payload.get("username") or "").strip().lower()
        password = str(payload.get("password") or "")
        if not username or not password:
            self.send_json({"error": "User ID and password are required."}, 400)
            return
        with connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ? AND isActive = 1", [username]).fetchone()
            if not row or not verify_password(password, row["passwordHash"]):
                self.send_json({"error": "Invalid user ID or password."}, 401)
                return
            token = secrets.token_urlsafe(32)
            expires = int(time.time()) + SESSION_TTL_SECONDS
            conn.execute("DELETE FROM sessions WHERE expiresAt <= ?", [int(time.time())])
            conn.execute(
                "INSERT INTO sessions(token, userId, createdAt, expiresAt) VALUES(?,?,?,?)",
                [token, row["id"], now_iso(), expires],
            )
            audit_event(conn, public_user(row), "login", "user", row["id"])
        cookie = f"{SESSION_COOKIE}={urllib.parse.quote(token)}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TTL_SECONDS}"
        self.send_json({"user": public_user(row)}, headers={"Set-Cookie": cookie})

    def logout(self):
        token = self.cookie_value(SESSION_COOKIE)
        if token:
            with connect() as conn:
                row = conn.execute("SELECT users.* FROM sessions JOIN users ON users.id = sessions.userId WHERE sessions.token = ?", [token]).fetchone()
                conn.execute("DELETE FROM sessions WHERE token = ?", [token])
                if row:
                    audit_event(conn, public_user(row), "logout", "user", row["id"])
        cookie = f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
        self.send_json({"ok": True}, headers={"Set-Cookie": cookie})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/api/me":
            self.send_json({"user": self.current_user()})
            return
        if parsed.path.startswith("/api/"):
            user = self.require_user()
            if not user:
                return
        else:
            user = None
        if parsed.path == "/api/tasks":
            self.send_json({"tasks": query_tasks(query, user)})
            return
        if parsed.path == "/api/analytics":
            self.send_json(analytics_for(query_tasks(query, user)))
            return
        if parsed.path == "/api/analytics/command-center":
            self.send_json(command_center_for(query_tasks(query, user)))
            return
        if parsed.path == "/api/options":
            with connect() as conn:
                result = {}
                visible_tasks = query_tasks({}, user)
                for field in ["brand", "bucket", "zone", "agency", "status", "owner", "bucketAdmin", "primaryOwner", "secondaryOwner", "reviewer", "priority"]:
                    result[field] = sorted({t.get(field) for t in visible_tasks if t.get(field)})
                result["roles"] = USER_ROLES
                result["assetTypes"] = ASSET_TYPES
                result["checklistSteps"] = CHECKLIST_STEPS
                result["users"] = all_users(conn)
            self.send_json(result)
            return
        if parsed.path == "/api/users":
            if not can_admin(role_from_user(user)):
                self.send_json({"error": "Only the super admin can manage users."}, 403)
                return
            with connect() as conn:
                self.send_json({"users": all_users(conn)})
            return
        if parsed.path == "/api/admin/access-matrix":
            if not can_admin(role_from_user(user)):
                self.send_json({"error": "Only the super admin can view the access matrix."}, 403)
                return
            with connect() as conn:
                self.send_json({"matrix": access_matrix(conn)})
            return
        if parsed.path == "/api/admin/audit":
            if not can_admin(role_from_user(user)):
                self.send_json({"error": "Only the super admin can view audit events."}, 403)
                return
            with connect() as conn:
                rows = conn.execute("SELECT * FROM system_audit ORDER BY id DESC LIMIT 120").fetchall()
            self.send_json({"events": [dict(r) for r in rows]})
            return
        if parsed.path == "/api/settings/deployment":
            if not can_admin(role_from_user(user)):
                self.send_json({"error": "Only the super admin can view deployment settings."}, 403)
                return
            self.send_json(deployment_status())
            return
        if parsed.path == "/api/my-work":
            name = user["displayName"]
            mine = [t for t in query_tasks(query, user) if name in [t.get("primaryOwner"), t.get("secondaryOwner"), t.get("bucketAdmin"), t.get("reviewer"), t.get("owner")]]
            self.send_json({"tasks": mine, "counts": analytics_for(mine)["cards"]})
            return
        if parsed.path == "/api/planning":
            tasks = query_tasks(query, user)
            timeline = [t for t in tasks if t.get("plannedStart") or t.get("deadline") or t.get("publishDate")]
            calendar = sorted(timeline, key=lambda t: t.get("deadline") or t.get("publishDate") or t.get("plannedStart") or "")[:80]
            self.send_json({"calendar": calendar, "missingDates": [t for t in tasks if not t.get("deadline")][:80], "timeline": timeline[:120]})
            return
        if parsed.path == "/api/notifications":
            with connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM notifications WHERE userId = ? ORDER BY isRead ASC, id DESC LIMIT 80",
                    [user["id"]],
                ).fetchall()
            self.send_json({"notifications": [dict(r) for r in rows]})
            return
        if parsed.path == "/api/notifications/digest":
            with connect() as conn:
                self.send_json(digest_for_user(conn, user))
            return
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/collaboration"):
            task_id = urllib.parse.unquote(parsed.path.split("/")[-2])
            with connect() as conn:
                if not can_access_task(conn, user, task_id):
                    self.send_json({"error": "Task not found."}, 404)
                    return
                self.send_json(task_collaboration(conn, task_id))
            return
        if parsed.path == "/api/activity":
            task_id = query.get("taskId", [""])[0]
            with connect() as conn:
                if not can_access_task(conn, user, task_id):
                    self.send_json({"error": "Task not found."}, 404)
                    return
                rows = conn.execute(
                    "SELECT * FROM activity_log WHERE taskId = ? ORDER BY id DESC LIMIT 30",
                    [task_id],
                ).fetchall()
            self.send_json({"activity": [dict(r) for r in rows]})
            return
        if parsed.path == "/api/tasks/export.csv":
            rows = query_tasks(query, user)
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=["id", *TASK_FIELDS, "createdAt", "updatedAt", "completedAt", "lastStageChangedAt"], extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            body = stream.getvalue().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=astral_video_tracker.csv")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/auth/login":
            self.login()
            return
        if parsed.path == "/api/auth/logout":
            self.logout()
            return
        if parsed.path == "/api/auth/request-reset":
            payload = self.read_json()
            username = str(payload.get("username") or "").strip().lower()
            if not username:
                self.send_json({"ok": True})
                return
            with connect() as conn:
                row = conn.execute("SELECT * FROM users WHERE username = ? AND isActive = 1", [username]).fetchone()
                if row:
                    token = secrets.token_urlsafe(32)
                    conn.execute(
                        "INSERT INTO password_reset_tokens(token,userId,createdAt,expiresAt,usedAt) VALUES(?,?,?,?, '')",
                        [token, row["id"], now_iso(), int(time.time()) + 3600],
                    )
                    notify_user(conn, row["id"], "", "Password reset requested", "Ask the super admin for a reset if email is not configured.")
                    audit_event(conn, public_user(row), "password_reset_requested", "user", row["id"], {"smtpConfigured": SMTP_CONFIGURED})
                    self.send_json({"ok": True, "emailConfigured": SMTP_CONFIGURED, "resetToken": token if not SMTP_CONFIGURED else ""})
                    return
            self.send_json({"ok": True, "emailConfigured": SMTP_CONFIGURED})
            return
        if parsed.path == "/api/auth/reset-password":
            payload = self.read_json()
            token = str(payload.get("token") or "")
            new_password = str(payload.get("newPassword") or "")
            if len(new_password) < 8:
                self.send_json({"error": "New password must be at least 8 characters."}, 400)
                return
            with connect() as conn:
                row = conn.execute(
                    """
                    SELECT password_reset_tokens.*, users.username, users.displayName, users.role, users.email, users.phone, users.team, users.agencyName, users.isAgencyUser, users.notificationPrefs, users.isActive, users.mustChangePassword
                    FROM password_reset_tokens JOIN users ON users.id = password_reset_tokens.userId
                    WHERE token = ? AND usedAt = '' AND expiresAt > ?
                    """,
                    [token, int(time.time())],
                ).fetchone()
                if not row:
                    self.send_json({"error": "Reset token is invalid or expired."}, 400)
                    return
                conn.execute(
                    "UPDATE users SET passwordHash = ?, mustChangePassword = 0, updatedAt = ? WHERE id = ?",
                    [hash_password(new_password), now_iso(), row["userId"]],
                )
                conn.execute("UPDATE password_reset_tokens SET usedAt = ? WHERE token = ?", [now_iso(), token])
                audit_event(conn, {"id": row["userId"], "displayName": row["displayName"]}, "password_reset_completed", "user", row["userId"])
            self.send_json({"ok": True})
            return
        user = self.require_user()
        if not user:
            return
        role = role_from_user(user)
        actor = user["displayName"]
        if parsed.path == "/api/tasks":
            if not can_write(role):
                self.send_json({"error": "Viewer role cannot create tasks."}, 403)
                return
            payload = self.read_json()
            payload["no"] = payload.get("no") or next_no()
            with connect() as conn:
                payload = canonicalize_task_people(conn, payload)
                task = normalize_task(payload)
                insert_many(conn, [task])
                ensure_task_checklist(conn, task["id"])
                self.log_activity(conn, task["id"], "create", actor, "", task)
                audit_event(conn, user, "task_created", "task", task["id"], {"title": task["title"]})
            self.send_json({"task": enrich_task(task)}, 201)
            return
        if parsed.path == "/api/users":
            if not can_admin(role):
                self.send_json({"error": "Only the super admin can create users."}, 403)
                return
            payload = self.read_json()
            username = str(payload.get("username") or "").strip().lower()
            display = str(payload.get("displayName") or username).strip()
            new_role = str(payload.get("role") or "editor")
            password = str(payload.get("password") or INITIAL_PASSWORD)
            if not username or new_role not in USER_ROLES:
                self.send_json({"error": "Valid username and role are required."}, 400)
                return
            if new_role == "super_admin" and username != "aniket":
                self.send_json({"error": "Aniket is the single super admin."}, 400)
                return
            ts = now_iso()
            with connect() as conn:
                if not username_available(conn, username):
                    self.send_json({"error": "That user ID already exists."}, 400)
                    return
                if not display_name_available(conn, display):
                    self.send_json({"error": "That display name already exists. Use the existing user to avoid owner duplication."}, 400)
                    return
                conn.execute(
                    """
                    INSERT INTO users(id,username,displayName,role,email,phone,team,agencyName,isAgencyUser,notificationPrefs,passwordHash,isActive,mustChangePassword,createdAt,updatedAt)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    [
                        f"user_{username}",
                        username,
                        display,
                        new_role,
                        str(payload.get("email") or ""),
                        str(payload.get("phone") or ""),
                        str(payload.get("team") or ""),
                        str(payload.get("agencyName") or ""),
                        1 if payload.get("isAgencyUser") or new_role == "agency" else 0,
                        json.dumps(payload.get("notificationPrefs") or {}),
                        hash_password(password),
                        1,
                        1,
                        ts,
                        ts,
                    ],
                )
                for item in payload.get("access", []) or []:
                    access_type = str(item.get("accessType") or "").strip()
                    access_value = str(item.get("accessValue") or "").strip()
                    if access_type and access_value:
                        conn.execute("INSERT OR IGNORE INTO user_access(userId,accessType,accessValue) VALUES(?,?,?)", [f"user_{username}", access_type, access_value])
                audit_event(conn, user, "user_created", "user", f"user_{username}", {"role": new_role})
                self.send_json({"users": all_users(conn)}, 201)
            return
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/comments"):
            if not can_collaborate(role):
                self.send_json({"error": "Your role cannot comment."}, 403)
                return
            task_id = urllib.parse.unquote(parsed.path.split("/")[-2])
            body = str(self.read_json().get("body") or "").strip()
            if not body:
                self.send_json({"error": "Comment cannot be empty."}, 400)
                return
            with connect() as conn:
                if not can_access_task(conn, user, task_id):
                    self.send_json({"error": "Task not found."}, 404)
                    return
                conn.execute("INSERT INTO task_comments(taskId,userId,body,createdAt) VALUES(?,?,?,?)", [task_id, user["id"], body, now_iso()])
                self.log_activity(conn, task_id, "comment added", actor, "", {"body": body})
                task = conn.execute("SELECT * FROM tasks WHERE id = ?", [task_id]).fetchone()
                for name in [task["primaryOwner"], task["secondaryOwner"], task["reviewer"]] if task else []:
                    target = user_by_name(conn, name)
                    if target and target["id"] != user["id"]:
                        notify_user(conn, target["id"], task_id, f"Comment on {task['title']}", body[:120])
                for mention in set(re.findall(r"@([A-Za-z0-9_]+)", body)):
                    target = user_by_name(conn, mention)
                    if target and target["id"] != user["id"]:
                        notify_user(conn, target["id"], task_id, f"{actor} mentioned you", body[:120])
                self.send_json(task_collaboration(conn, task_id), 201)
            return
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/assets"):
            if not can_collaborate(role):
                self.send_json({"error": "Your role cannot add assets."}, 403)
                return
            task_id = urllib.parse.unquote(parsed.path.split("/")[-2])
            payload = self.read_json()
            asset_type = str(payload.get("assetType") or "Link").strip()
            if asset_type not in ASSET_TYPES:
                asset_type = "Other"
            label = str(payload.get("label") or asset_type).strip()
            url = str(payload.get("url") or "").strip()
            if not url:
                self.send_json({"error": "Asset URL is required."}, 400)
                return
            with connect() as conn:
                if not can_access_task(conn, user, task_id):
                    self.send_json({"error": "Task not found."}, 404)
                    return
                conn.execute("INSERT INTO task_assets(taskId,userId,assetType,label,url,createdAt) VALUES(?,?,?,?,?,?)", [task_id, user["id"], asset_type, label, url, now_iso()])
                self.log_activity(conn, task_id, "asset added", actor, "", {"assetType": asset_type, "label": label, "url": url})
                self.send_json(task_collaboration(conn, task_id), 201)
            return
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/review"):
            if not can_review(role):
                self.send_json({"error": "Your role cannot review tasks."}, 403)
                return
            task_id = urllib.parse.unquote(parsed.path.split("/")[-2])
            payload = self.read_json()
            decision = str(payload.get("decision") or "").strip()
            note = str(payload.get("note") or "").strip()
            if decision not in ["approved", "changes_requested", "ready", "published"]:
                self.send_json({"error": "Invalid review decision."}, 400)
                return
            status_by_decision = {"approved": "Ready", "changes_requested": "In Review", "ready": "Ready", "published": "Published"}
            with connect() as conn:
                before = conn.execute("SELECT * FROM tasks WHERE id = ?", [task_id]).fetchone()
                if not before or not can_access_task(conn, user, task_id):
                    self.send_json({"error": "Task not found."}, 404)
                    return
                conn.execute("INSERT INTO approval_events(taskId,userId,decision,note,createdAt) VALUES(?,?,?,?,?)", [task_id, user["id"], decision, note, now_iso()])
                merged = dict(before)
                merged["status"] = status_by_decision[decision]
                if decision == "published":
                    merged["publishDate"] = time.strftime("%Y-%m-%d")
                    merged["completedAt"] = merged.get("completedAt") or now_iso()
                task = normalize_task(merged, before)
                sets = ",".join([f"{k}=:{k}" for k in task.keys() if k != "id"])
                conn.execute(f"UPDATE tasks SET {sets} WHERE id=:id", task)
                self.log_activity(conn, task_id, f"review {decision}", actor, dict(before), task)
                owner = user_by_name(conn, task.get("primaryOwner"))
                if owner and owner["id"] != user["id"]:
                    notify_user(conn, owner["id"], task_id, f"Review update: {task['title']}", decision.replace("_", " "))
                if decision == "published":
                    for name in [task.get("secondaryOwner"), task.get("bucketAdmin")]:
                        target = user_by_name(conn, name)
                        if target and target["id"] != user["id"]:
                            notify_user(conn, target["id"], task_id, f"Published: {task['title']}", "This task is now marked published.")
                audit_event(conn, user, f"review_{decision}", "task", task_id, {"title": task["title"]})
                self.send_json({"task": enrich_task(task), **task_collaboration(conn, task_id)})
            return
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/checklist"):
            if not can_collaborate(role):
                self.send_json({"error": "Your role cannot update checklists."}, 403)
                return
            task_id = urllib.parse.unquote(parsed.path.split("/")[-2])
            payload = self.read_json()
            step = str(payload.get("step") or "").strip()
            is_done = 1 if payload.get("isDone") else 0
            if step not in CHECKLIST_STEPS:
                self.send_json({"error": "Invalid checklist step."}, 400)
                return
            with connect() as conn:
                if not can_access_task(conn, user, task_id):
                    self.send_json({"error": "Task not found."}, 404)
                    return
                ensure_task_checklist(conn, task_id)
                conn.execute(
                    "UPDATE task_checklists SET isDone = ?, updatedBy = ?, updatedAt = ? WHERE taskId = ? AND step = ?",
                    [is_done, actor, now_iso(), task_id, step],
                )
                self.log_activity(conn, task_id, f"checklist {step} {'done' if is_done else 'reopened'}", actor, "", {"step": step, "isDone": is_done})
                self.send_json(task_collaboration(conn, task_id))
            return
        if parsed.path == "/api/tasks/import":
            if not can_admin(role):
                self.send_json({"error": "Only the super admin can import CSV."}, 403)
                return
            length = int(self.headers.get("Content-Length", "0"))
            text = self.rfile.read(length).decode("utf-8")
            reader = csv.DictReader(io.StringIO(text))
            imported = []
            with connect() as conn:
                for raw in reader:
                    existing = None
                    if raw.get("id"):
                        existing = conn.execute("SELECT * FROM tasks WHERE id = ?", [raw["id"]]).fetchone()
                    raw = canonicalize_task_people(conn, raw)
                    task = normalize_task(raw, existing)
                    if existing:
                        sets = ",".join([f"{k}=:{k}" for k in task.keys() if k != "id"])
                        conn.execute(f"UPDATE tasks SET {sets} WHERE id=:id", task)
                        self.log_activity(conn, task["id"], "import_update", actor, dict(existing), task)
                    else:
                        insert_many(conn, [task])
                        ensure_task_checklist(conn, task["id"])
                        self.log_activity(conn, task["id"], "import_create", actor, "", task)
                    imported.append(task)
                audit_event(conn, user, "tasks_imported", "task", "", {"count": len(imported)})
            self.send_json({"imported": len(imported)})
            return
        if parsed.path == "/api/tasks/reset":
            if not can_admin(role):
                self.send_json({"error": "Only the super admin can reset tasks."}, 403)
                return
            with connect() as conn:
                conn.execute("DELETE FROM tasks")
                conn.execute("DELETE FROM activity_log")
                seed_tasks(conn)
                audit_event(conn, user, "tasks_reset", "task", "", {})
            self.send_json({"ok": True})
            return
        self.send_json({"error": "Not found"}, 404)

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        user = self.require_user()
        if not user:
            return
        role = role_from_user(user)
        actor = user["displayName"]
        if parsed.path.startswith("/api/users/"):
            if not can_admin(role):
                self.send_json({"error": "Only the super admin can update users."}, 403)
                return
            user_id = urllib.parse.unquote(parsed.path.split("/")[-1])
            payload = self.read_json()
            allowed = {}
            if "displayName" in payload:
                allowed["displayName"] = str(payload["displayName"]).strip()
            for field in ["email", "phone", "team", "agencyName"]:
                if field in payload:
                    allowed[field] = str(payload[field] or "").strip()
            if "isAgencyUser" in payload:
                allowed["isAgencyUser"] = 1 if payload["isAgencyUser"] else 0
            if "notificationPrefs" in payload:
                allowed["notificationPrefs"] = json.dumps(payload["notificationPrefs"] or {})
            if "role" in payload:
                new_role = str(payload["role"])
                if new_role not in USER_ROLES:
                    self.send_json({"error": "Invalid role."}, 400)
                    return
                if new_role == "super_admin" and user_id != "user_aniket":
                    self.send_json({"error": "Aniket is the single super admin."}, 400)
                    return
                allowed["role"] = new_role
            if "isActive" in payload:
                allowed["isActive"] = 1 if payload["isActive"] else 0
            if "password" in payload and payload["password"]:
                allowed["passwordHash"] = hash_password(str(payload["password"]))
                allowed["mustChangePassword"] = 1
            if not allowed:
                self.send_json({"error": "No user changes supplied."}, 400)
                return
            allowed["updatedAt"] = now_iso()
            with connect() as conn:
                if "displayName" in allowed and not display_name_available(conn, allowed["displayName"], user_id):
                    self.send_json({"error": "That display name already exists. Use unique names to protect owner analytics."}, 400)
                    return
                if "role" in allowed and user_id == "user_aniket":
                    conn.execute("UPDATE users SET role='admin' WHERE role='super_admin' AND id != 'user_aniket'")
                sets = ",".join([f"{k}=?" for k in allowed])
                conn.execute(f"UPDATE users SET {sets} WHERE id=?", [*allowed.values(), user_id])
                conn.execute("UPDATE users SET role='super_admin', isActive=1 WHERE id='user_aniket'")
                if "access" in payload:
                    conn.execute("DELETE FROM user_access WHERE userId = ?", [user_id])
                    for item in payload.get("access") or []:
                        access_type = str(item.get("accessType") or "").strip()
                        access_value = str(item.get("accessValue") or "").strip()
                        if access_type and access_value:
                            conn.execute("INSERT OR IGNORE INTO user_access(userId,accessType,accessValue) VALUES(?,?,?)", [user_id, access_type, access_value])
                audit_event(conn, user, "user_updated", "user", user_id, {"fields": sorted(allowed.keys())})
                self.send_json({"users": all_users(conn)})
            return
        if parsed.path == "/api/me/preferences":
            payload = self.read_json()
            prefs = payload.get("notificationPrefs") or {}
            with connect() as conn:
                conn.execute("UPDATE users SET notificationPrefs = ?, updatedAt = ? WHERE id = ?", [json.dumps(prefs), now_iso(), user["id"]])
                refreshed = conn.execute("SELECT * FROM users WHERE id = ?", [user["id"]]).fetchone()
            self.send_json({"user": public_user(refreshed)})
            return
        if parsed.path == "/api/me/password":
            payload = self.read_json()
            current_password = str(payload.get("currentPassword") or "")
            new_password = str(payload.get("newPassword") or "")
            if len(new_password) < 8:
                self.send_json({"error": "New password must be at least 8 characters."}, 400)
                return
            with connect() as conn:
                row = conn.execute("SELECT * FROM users WHERE id = ? AND isActive = 1", [user["id"]]).fetchone()
                if not row or not verify_password(current_password, row["passwordHash"]):
                    self.send_json({"error": "Current password is incorrect."}, 400)
                    return
                conn.execute(
                    "UPDATE users SET passwordHash = ?, mustChangePassword = 0, updatedAt = ? WHERE id = ?",
                    [hash_password(new_password), now_iso(), user["id"]],
                )
                refreshed = conn.execute("SELECT * FROM users WHERE id = ?", [user["id"]]).fetchone()
            self.send_json({"user": public_user(refreshed)})
            return
        if parsed.path.startswith("/api/notifications/"):
            notif_id = urllib.parse.unquote(parsed.path.split("/")[-1])
            with connect() as conn:
                conn.execute("UPDATE notifications SET isRead = 1 WHERE id = ? AND userId = ?", [notif_id, user["id"]])
            self.send_json({"ok": True})
            return
        if parsed.path == "/api/tasks/bulk":
            if not can_write(role):
                self.send_json({"error": "Viewer role cannot bulk edit tasks."}, 403)
                return
            payload = self.read_json()
            ids = payload.get("ids") or []
            changes = {k: payload.get("changes", {}).get(k) for k in payload.get("changes", {}) if k in set(TASK_FIELDS)}
            if not ids or not changes:
                self.send_json({"error": "Bulk edit requires ids and editable changes."}, 400)
                return
            updated = []
            with connect() as conn:
                changes = canonicalize_task_people(conn, changes)
                for task_id in ids:
                    before = conn.execute("SELECT * FROM tasks WHERE id = ?", [task_id]).fetchone()
                    if not before or not can_access_task(conn, user, task_id):
                        continue
                    merged = dict(before)
                    merged.update(changes)
                    task = normalize_task(merged, before)
                    sets = ",".join([f"{k}=:{k}" for k in task.keys() if k != "id"])
                    conn.execute(f"UPDATE tasks SET {sets} WHERE id=:id", task)
                    self.log_activity(conn, task_id, action_label(dict(before), task, bulk=True), actor, dict(before), task)
                    self.notify_assignment_changes(conn, task_id, dict(before), task, actor)
                    if task.get("deadline") and not before["deadline"]:
                        owner = user_by_name(conn, task.get("primaryOwner"))
                        if owner:
                            notify_user(conn, owner["id"], task_id, f"Expected date set: {task['title']}", task["deadline"])
                    updated.append(task)
                audit_event(conn, user, "tasks_bulk_updated", "task", "", {"count": len(updated), "fields": sorted(changes.keys())})
            self.send_json({"updated": len(updated), "tasks": [enrich_task(t) for t in updated]})
            return
        if not parsed.path.startswith("/api/tasks/"):
            self.send_json({"error": "Not found"}, 404)
            return
        if not can_write(role):
            self.send_json({"error": "Viewer role cannot edit tasks."}, 403)
            return
        task_id = urllib.parse.unquote(parsed.path.split("/")[-1])
        payload = self.read_json()
        allowed = set(TASK_FIELDS)
        changes = {k: payload[k] for k in payload if k in allowed}
        if not changes:
            self.send_json({"error": "No editable fields supplied."}, 400)
            return
        with connect() as conn:
            before = conn.execute("SELECT * FROM tasks WHERE id = ?", [task_id]).fetchone()
            if not before or not can_access_task(conn, user, task_id):
                self.send_json({"error": "Task not found."}, 404)
                return
            changes = canonicalize_task_people(conn, changes)
            merged = dict(before)
            merged.update(changes)
            task = normalize_task(merged, before)
            sets = ",".join([f"{k}=:{k}" for k in task.keys() if k != "id"])
            conn.execute(f"UPDATE tasks SET {sets} WHERE id=:id", task)
            self.log_activity(conn, task_id, action_label(dict(before), task), actor, dict(before), task)
            self.notify_assignment_changes(conn, task_id, dict(before), task, actor)
            if task.get("status") == "Ready" and before["status"] != "Ready":
                target = user_by_name(conn, task.get("bucketAdmin"))
                if target:
                    notify_user(conn, target["id"], task_id, f"Ready to publish: {task['title']}", "This item is ready for final publishing.")
            audit_event(conn, user, "task_updated", "task", task_id, {"fields": sorted(changes.keys())})
        self.send_json({"task": enrich_task(task)})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        user = self.require_user()
        if not user:
            return
        role = role_from_user(user)
        actor = user["displayName"]
        if not parsed.path.startswith("/api/tasks/"):
            self.send_json({"error": "Not found"}, 404)
            return
        if not can_admin(role):
            self.send_json({"error": "Only the super admin can delete tasks."}, 403)
            return
        task_id = urllib.parse.unquote(parsed.path.split("/")[-1])
        with connect() as conn:
            before = conn.execute("SELECT * FROM tasks WHERE id = ?", [task_id]).fetchone()
            if not before:
                self.send_json({"error": "Task not found."}, 404)
                return
            conn.execute("DELETE FROM tasks WHERE id = ?", [task_id])
            self.log_activity(conn, task_id, "delete", actor, dict(before), "")
            audit_event(conn, user, "task_deleted", "task", task_id, {"title": before["title"]})
        self.send_json({"ok": True})

    def log_activity(self, conn, task_id, action, role, before, after):
        conn.execute(
            "INSERT INTO activity_log(taskId,action,actorRole,changedAt,beforeJson,afterJson) VALUES(?,?,?,?,?,?)",
            [task_id, action, role, now_iso(), json.dumps(before), json.dumps(after)],
        )

    def notify_assignment_changes(self, conn, task_id, before, after, actor):
        for field, label in [("primaryOwner", "Primary owner"), ("secondaryOwner", "Secondary owner"), ("bucketAdmin", "Bucket admin"), ("reviewer", "Reviewer")]:
            if before.get(field) == after.get(field) or not after.get(field):
                continue
            target = user_by_name(conn, after.get(field))
            if target:
                notify_user(conn, target["id"], task_id, f"{label} assigned", f"{actor} assigned you on {after.get('title')}")

    def serve_static(self, path):
        rel = "index.html" if path in ["", "/"] else path.lstrip("/")
        target = (PUBLIC / rel).resolve()
        if not str(target).startswith(str(PUBLIC)) or not target.exists() or target.is_dir():
            target = PUBLIC / "index.html"
        content_type = "text/plain"
        if target.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif target.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "3401"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Astral Taskmaster running at http://127.0.0.1:{port}")
    server.serve_forever()
