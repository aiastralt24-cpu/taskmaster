import csv
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import time
import urllib.parse
from pathlib import Path

import psycopg
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "seed" / "AstralVideoTracker.jsx"
PUBLIC_DIR = ROOT / "public"

DATABASE_URL = os.environ.get("DATABASE_URL", "")
APP_URL = os.environ.get("TASKMASTER_APP_URL", "https://taskmaster.vercel.app")
SESSION_COOKIE = "taskmaster_session"
SESSION_TTL_SECONDS = 14 * 86400
INITIAL_PASSWORD = os.environ.get("TASKMASTER_INITIAL_PASSWORD", "Taskmaster@2026")
SMTP_CONFIGURED = bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))

STATUSES = ["Concept Stage", "Scripting", "In Production", "In Review", "Ready", "Completed", "Published", "On Hold"]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]
USER_ROLES = ["super_admin", "admin", "editor", "reviewer", "agency", "viewer"]
ASSET_TYPES = ["Script", "Raw Footage", "Edit Link", "Final Video", "Thumbnail", "Published URL", "Reference", "Other"]
CHECKLIST_STEPS = ["script", "shoot/design", "edit", "review", "publish"]
ACTIVE_STATUSES = ["Scripting", "In Production", "In Review", "Ready"]
DONE_STATUSES = ["Completed", "Published"]
STUCK_DAYS = 7
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
    "no", "brand", "bucket", "zone", "title", "length", "hook", "agency", "status", "owner",
    "bucketAdmin", "primaryOwner", "secondaryOwner", "reviewer", "deadline", "plannedStart",
    "publishDate", "actualCompletionDate", "delayReason", "assignmentStatus", "priority", "notes",
]
SEEDED_USERS = [
    {"username": "jay", "displayName": "Jay", "role": "admin", "team": "Content", "access": [("bucket", "NON-AI Product Video"), ("bucket", "Project Case Study"), ("bucket", "Testimonial-Dealer")]},
    {"username": "yogen", "displayName": "Yogen", "role": "admin", "team": "Content", "access": []},
    {"username": "vaibhav", "displayName": "Vaibhav", "role": "editor", "team": "Production", "access": []},
    {"username": "aniket", "displayName": "Aniket", "role": "super_admin", "team": "Command", "access": []},
    {"username": "akash", "displayName": "Akash", "role": "editor", "team": "Production", "access": []},
    {"username": "arvind", "displayName": "Arvind", "role": "editor", "team": "Production", "access": []},
]

app = FastAPI()
_initialized = False


def json_response(value, status=200, headers=None):
    return JSONResponse(value, status_code=status, headers=headers or {})


def error(message, status=400):
    return json_response({"error": message}, status)


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def today_date():
    return time.strftime("%Y-%m-%d")


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


def conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required for the Vercel API.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)


def qmarks(values, start=1):
    return ",".join(["%s"] * len(values))


def init_db():
    global _initialized
    if _initialized:
        return
    with conn() as db:
        with db.cursor() as cur:
            cur.execute("SET statement_timeout = '60s'")
            cur.execute("SET lock_timeout = '20s'")
            cur.execute("SELECT pg_advisory_xact_lock(2606173401)")
            cur.execute(
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
                  "bucketAdmin" TEXT DEFAULT '',
                  "primaryOwner" TEXT DEFAULT '',
                  "secondaryOwner" TEXT DEFAULT '',
                  reviewer TEXT DEFAULT '',
                  deadline TEXT DEFAULT '',
                  "plannedStart" TEXT DEFAULT '',
                  "publishDate" TEXT DEFAULT '',
                  "actualCompletionDate" TEXT DEFAULT '',
                  "delayReason" TEXT DEFAULT '',
                  "assignmentStatus" TEXT DEFAULT 'assigned',
                  priority TEXT DEFAULT 'Medium',
                  notes TEXT DEFAULT '',
                  "createdAt" TEXT NOT NULL,
                  "updatedAt" TEXT NOT NULL,
                  "completedAt" TEXT DEFAULT '',
                  "lastStageChangedAt" TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS activity_log (
                  id BIGSERIAL PRIMARY KEY,
                  "taskId" TEXT NOT NULL,
                  action TEXT NOT NULL,
                  "actorRole" TEXT NOT NULL,
                  "changedAt" TEXT NOT NULL,
                  "beforeJson" TEXT DEFAULT '',
                  "afterJson" TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS users (
                  id TEXT PRIMARY KEY,
                  username TEXT NOT NULL UNIQUE,
                  "displayName" TEXT NOT NULL,
                  role TEXT NOT NULL,
                  email TEXT DEFAULT '',
                  phone TEXT DEFAULT '',
                  team TEXT DEFAULT '',
                  "agencyName" TEXT DEFAULT '',
                  "isAgencyUser" BOOLEAN NOT NULL DEFAULT FALSE,
                  "notificationPrefs" TEXT DEFAULT '{}',
                  "passwordHash" TEXT NOT NULL,
                  "isActive" BOOLEAN NOT NULL DEFAULT TRUE,
                  "mustChangePassword" BOOLEAN NOT NULL DEFAULT TRUE,
                  "createdAt" TEXT NOT NULL,
                  "updatedAt" TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                  token TEXT PRIMARY KEY,
                  "userId" TEXT NOT NULL REFERENCES users(id),
                  "createdAt" TEXT NOT NULL,
                  "expiresAt" BIGINT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS user_access (
                  id BIGSERIAL PRIMARY KEY,
                  "userId" TEXT NOT NULL,
                  "accessType" TEXT NOT NULL,
                  "accessValue" TEXT NOT NULL,
                  UNIQUE("userId", "accessType", "accessValue")
                );
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                  token TEXT PRIMARY KEY,
                  "userId" TEXT NOT NULL,
                  "createdAt" TEXT NOT NULL,
                  "expiresAt" BIGINT NOT NULL,
                  "usedAt" TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS task_comments (
                  id BIGSERIAL PRIMARY KEY,
                  "taskId" TEXT NOT NULL,
                  "userId" TEXT NOT NULL,
                  body TEXT NOT NULL,
                  "createdAt" TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS task_assets (
                  id BIGSERIAL PRIMARY KEY,
                  "taskId" TEXT NOT NULL,
                  "userId" TEXT NOT NULL,
                  "assetType" TEXT NOT NULL,
                  label TEXT NOT NULL,
                  url TEXT NOT NULL,
                  "createdAt" TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approval_events (
                  id BIGSERIAL PRIMARY KEY,
                  "taskId" TEXT NOT NULL,
                  "userId" TEXT NOT NULL,
                  decision TEXT NOT NULL,
                  note TEXT DEFAULT '',
                  "createdAt" TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS notifications (
                  id BIGSERIAL PRIMARY KEY,
                  "userId" TEXT NOT NULL,
                  "taskId" TEXT DEFAULT '',
                  title TEXT NOT NULL,
                  body TEXT DEFAULT '',
                  channel TEXT NOT NULL DEFAULT 'in_app',
                  "deliveryStatus" TEXT NOT NULL DEFAULT 'queued',
                  "isRead" BOOLEAN NOT NULL DEFAULT FALSE,
                  "createdAt" TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS task_checklists (
                  id BIGSERIAL PRIMARY KEY,
                  "taskId" TEXT NOT NULL,
                  step TEXT NOT NULL,
                  "isDone" BOOLEAN NOT NULL DEFAULT FALSE,
                  "updatedBy" TEXT DEFAULT '',
                  "updatedAt" TEXT NOT NULL,
                  UNIQUE("taskId", step)
                );
                CREATE TABLE IF NOT EXISTS system_audit (
                  id BIGSERIAL PRIMARY KEY,
                  "actorUserId" TEXT DEFAULT '',
                  "actorName" TEXT DEFAULT '',
                  action TEXT NOT NULL,
                  "subjectType" TEXT DEFAULT '',
                  "subjectId" TEXT DEFAULT '',
                  "metadataJson" TEXT DEFAULT '',
                  "createdAt" TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions("userId");
                CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications("userId", "isRead");
                """
            )
            cur.execute("SELECT COUNT(*) AS c FROM users")
            if cur.fetchone()["c"] == 0:
                seed_users(cur)
            cur.execute("SELECT COUNT(*) AS c FROM tasks")
            if cur.fetchone()["c"] == 0:
                seed_tasks(cur)
            db.commit()
    _initialized = True


def parse_seed():
    text = SEED_PATH.read_text(encoding="utf-8")
    match = re.search(r"const SEED = (\[[\s\S]*?\]);;", text)
    if not match:
        raise RuntimeError("Could not find SEED array.")
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
    stage_changed = row.get("lastStageChangedAt") or (existing.get("lastStageChangedAt") if existing else "")
    if not stage_changed or (existing and previous_status != status):
        stage_changed = ts
    return {
        "id": row.get("id") or f"task_{int(time.time() * 1000)}_{secrets.token_hex(3)}",
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
        "createdAt": row.get("createdAt") or (existing.get("createdAt") if existing else ts),
        "updatedAt": ts,
        "completedAt": completed,
        "lastStageChangedAt": stage_changed,
    }


def seed_users(cur):
    ts = now_iso()
    for user in SEEDED_USERS:
        user_id = f"user_{user['username']}"
        cur.execute(
            """
            INSERT INTO users(id, username, "displayName", role, email, phone, team, "agencyName", "isAgencyUser", "notificationPrefs", "passwordHash", "isActive", "mustChangePassword", "createdAt", "updatedAt")
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,TRUE,%s,%s)
            ON CONFLICT (id) DO UPDATE SET "displayName" = EXCLUDED."displayName", role = EXCLUDED.role, team = EXCLUDED.team, "updatedAt" = EXCLUDED."updatedAt"
            """,
            [user_id, user["username"], user["displayName"], user["role"], user.get("email", ""), user.get("phone", ""), user.get("team", ""), user.get("agencyName", ""), user.get("role") == "agency", "{}", hash_password(INITIAL_PASSWORD), ts, ts],
        )
        for access_type, access_value in user.get("access", []):
            cur.execute(
                'INSERT INTO user_access("userId","accessType","accessValue") VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',
                [user_id, access_type, access_value],
            )
    cur.execute("UPDATE users SET role = 'admin' WHERE role = 'super_admin' AND username != 'aniket'")
    cur.execute('UPDATE users SET role = %s, "isActive" = TRUE, "updatedAt" = %s WHERE username = %s', ["super_admin", ts, "aniket"])


def seed_tasks(cur):
    ts = now_iso()
    for item in parse_seed():
        item["id"] = f"seed_{int(item.get('no') or 0):03d}"
        item["priority"] = "Medium"
        item["notes"] = ""
        item["createdAt"] = ts
        item["updatedAt"] = ts
        item["completedAt"] = ts if item.get("status") in DONE_STATUSES else ""
        item["lastStageChangedAt"] = ts
        insert_task(cur, normalize_task(item))


def insert_task(cur, task):
    fields = ["id", *TASK_FIELDS, "createdAt", "updatedAt", "completedAt", "lastStageChangedAt"]
    cols = ", ".join([quote_ident(f) for f in fields])
    cur.execute(
        f"INSERT INTO tasks({cols}) VALUES({qmarks(fields)}) ON CONFLICT (id) DO NOTHING",
        [task.get(f, "") for f in fields],
    )
    ensure_task_checklist(cur, task["id"])


def quote_ident(name):
    return f'"{name}"' if name != name.lower() or name in {"no"} else name


def public_user(row):
    if not row:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "displayName": row["displayName"],
        "role": row["role"],
        "email": row.get("email") or "",
        "phone": row.get("phone") or "",
        "team": row.get("team") or "",
        "agencyName": row.get("agencyName") or "",
        "isAgencyUser": bool(row.get("isAgencyUser")),
        "notificationPrefs": safe_json(row.get("notificationPrefs") or "{}", {}),
        "isActive": bool(row.get("isActive")),
        "mustChangePassword": bool(row.get("mustChangePassword")),
    }


def safe_json(value, fallback):
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


def all_users(cur):
    cur.execute('SELECT * FROM users ORDER BY role = %s DESC, "displayName"', ["super_admin"])
    rows = cur.fetchall()
    result = []
    for row in rows:
        item = public_user(row)
        cur.execute('SELECT "accessType", "accessValue" FROM user_access WHERE "userId" = %s ORDER BY "accessType", "accessValue"', [row["id"]])
        item["access"] = cur.fetchall()
        result.append(item)
    return result


def user_by_name(cur, name):
    if not name:
        return None
    cur.execute('SELECT * FROM users WHERE LOWER("displayName") = LOWER(%s) OR LOWER(username) = LOWER(%s) LIMIT 1', [name, name])
    return cur.fetchone()


def notify_user(cur, user_id, task_id, title, body=""):
    if user_id:
        cur.execute(
            'INSERT INTO notifications("userId","taskId",title,body,channel,"deliveryStatus","isRead","createdAt") VALUES(%s,%s,%s,%s,%s,%s,FALSE,%s)',
            [user_id, task_id or "", title, body, "in_app", "queued", now_iso()],
        )


def audit_event(cur, actor=None, action="", subject_type="", subject_id="", metadata=None):
    actor = actor or {}
    cur.execute(
        'INSERT INTO system_audit("actorUserId","actorName",action,"subjectType","subjectId","metadataJson","createdAt") VALUES(%s,%s,%s,%s,%s,%s,%s)',
        [actor.get("id", ""), actor.get("displayName", ""), action, subject_type, subject_id, json.dumps(metadata or {}), now_iso()],
    )


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


def require_database():
    try:
        init_db()
    except Exception as exc:
        return error(f"Database unavailable: {exc}", 500)
    return None


async def current_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE, "")
    if not token:
        return None
    init_db()
    with conn() as db:
        with db.cursor() as cur:
            cur.execute(
                'SELECT users.* FROM sessions JOIN users ON users.id = sessions."userId" WHERE sessions.token = %s AND sessions."expiresAt" > %s AND users."isActive" = TRUE',
                [token, int(time.time())],
            )
            return public_user(cur.fetchone())


async def require_user(request: Request):
    user = await current_user(request)
    if not user:
        return None, error("Login required.", 401)
    return user, None


def build_filters(params, user=None):
    clauses, values = [], []
    exacts = {
        "brand": "brand", "bucket": "bucket", "zone": "zone", "agency": "agency", "status": "status",
        "owner": "owner", "bucketAdmin": '"bucketAdmin"', "primaryOwner": '"primaryOwner"',
        "secondaryOwner": '"secondaryOwner"', "reviewer": "reviewer", "priority": "priority",
    }
    for qk, col in exacts.items():
        val = params.get(qk, "")
        if val and val != "All":
            clauses.append(f"{col} = %s")
            values.append(val)
    q = (params.get("q") or "").strip().lower()
    if q:
        clauses.append('(LOWER(title) LIKE %s OR LOWER(hook) LIKE %s OR LOWER(owner) LIKE %s OR LOWER(zone) LIKE %s OR LOWER(agency) LIKE %s)')
        values.extend([f"%{q}%"] * 5)
    start, end = params.get("deadlineFrom", ""), params.get("deadlineTo", "")
    if start:
        clauses.append("deadline >= %s")
        values.append(start)
    if end:
        clauses.append("deadline <= %s")
        values.append(end)
    overdue = params.get("overdue", "")
    if overdue == "overdue":
        clauses.append("deadline != '' AND deadline < %s AND status NOT IN ('Completed','Published')")
        values.append(today_date())
    elif overdue == "no-deadline":
        clauses.append("(deadline = '' OR deadline IS NULL)")
    quick = params.get("quickFilter", "")
    if quick == "needs-owner":
        clauses.append('("primaryOwner" = \'\' OR "primaryOwner" IS NULL)')
    elif quick == "needs-secondary":
        clauses.append('("secondaryOwner" = \'\' OR "secondaryOwner" IS NULL)')
    elif quick == "needs-admin":
        clauses.append('("bucketAdmin" = \'\' OR "bucketAdmin" IS NULL)')
    elif quick == "needs-deadline":
        clauses.append("(deadline = '' OR deadline IS NULL)")
    elif quick == "in-review":
        clauses.append("status = 'In Review'")
    elif quick == "ready-to-publish":
        clauses.append("status IN ('Ready','Completed')")
    elif quick == "active":
        clauses.append("status IN ('Scripting','In Production','In Review','Ready')")
    elif quick == "completed":
        clauses.append("status = 'Completed'")
    elif quick == "published":
        clauses.append("status = 'Published'")
    if user:
        v_clause, v_values = visibility_clause(user)
        if v_clause:
            clauses.append(v_clause)
            values.extend(v_values)
    return clauses, values


def access_values(user_id, access_type):
    with conn() as db:
        with db.cursor() as cur:
            cur.execute('SELECT "accessValue" FROM user_access WHERE "userId" = %s AND "accessType" = %s', [user_id, access_type])
            return [r["accessValue"] for r in cur.fetchall()]


def visibility_clause(user):
    if not user:
        return "1 = 0", []
    role = role_from_user(user)
    if role == "super_admin":
        return "", []
    buckets, agencies = access_values(user["id"], "bucket"), access_values(user["id"], "agency")
    if role == "admin" and (buckets or agencies):
        parts, vals = [], []
        if buckets:
            parts.append(f"bucket IN ({qmarks(buckets)})")
            vals.extend(buckets)
        if agencies:
            parts.append(f"agency IN ({qmarks(agencies)})")
            vals.extend(agencies)
        return "(" + " OR ".join(parts) + ")", vals
    if role == "agency":
        agency_values = [user.get("agencyName") or "", *agencies]
        agency_values = [a for a in dict.fromkeys(agency_values) if a]
        if agency_values:
            return f"agency IN ({qmarks(agency_values)})", agency_values
    names = [n for n in {str(user.get("displayName") or "").lower(), str(user.get("username") or "").lower()} if n]
    if not names:
        return "1 = 0", []
    fields = ["owner", '"bucketAdmin"', '"primaryOwner"', '"secondaryOwner"', "reviewer", "agency"]
    parts, vals = [], []
    for field in fields:
        parts.append(f"LOWER({field}) IN ({qmarks(names)})")
        vals.extend(names)
    return "(" + " OR ".join(parts) + ")", vals


def task_risk(t):
    deadline = t.get("deadline") or ""
    status = t.get("status") or "Concept Stage"
    age = days_since(t.get("lastStageChangedAt") or t.get("updatedAt") or t.get("createdAt"))
    end_week = time.strftime("%Y-%m-%d", time.localtime(time.time() + 6 * 86400))
    return {
        "missingOwner": not bool(t.get("primaryOwner") or t.get("owner")),
        "missingPrimary": not bool(t.get("primaryOwner") or t.get("owner")),
        "missingSecondary": not bool(t.get("secondaryOwner")),
        "missingAdmin": not bool(t.get("bucketAdmin")),
        "missingDeadline": not bool(deadline),
        "overdue": bool(deadline and deadline < today_date() and status not in DONE_STATUSES),
        "dueSoon": bool(deadline and today_date() <= deadline <= end_week and status not in DONE_STATUSES),
        "stuck": bool(status == "In Review" and age >= STUCK_DAYS),
        "readyToPublish": status in ["Ready", "Completed"],
        "stageAgeDays": age,
    }


def days_since(iso_value):
    if not iso_value:
        return 0
    try:
        then = time.mktime(time.strptime(iso_value[:19] + "Z", "%Y-%m-%dT%H:%M:%SZ"))
    except Exception:
        return 0
    return max(0, int((time.time() - then) // 86400))


def task_to_dict(row, user=None):
    task = dict(row)
    task["risk"] = task_risk(task)
    if user and role_from_user(user) == "agency":
        task["notes"] = ""
        task["hook"] = ""
        task["bucketAdmin"] = ""
    return task


def query_tasks(params, user=None):
    clauses, values = build_filters(params, user)
    sql = "SELECT * FROM tasks"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY CASE WHEN deadline = '' THEN 1 ELSE 0 END, deadline ASC, no ASC"
    with conn() as db:
        with db.cursor() as cur:
            cur.execute(sql, values)
            return [task_to_dict(r, user) for r in cur.fetchall()]


def analytics_for(tasks):
    today, end_week = today_date(), time.strftime("%Y-%m-%d", time.localtime(time.time() + 6 * 86400))
    cards = {
        "total": len(tasks),
        "inPipeline": sum(1 for t in tasks if t["status"] in ACTIVE_STATUSES),
        "published": sum(1 for t in tasks if t["status"] == "Published"),
        "completed": sum(1 for t in tasks if t["status"] == "Completed"),
        "overdue": sum(1 for t in tasks if t.get("deadline") and t["deadline"] < today and t["status"] not in DONE_STATUSES),
        "dueThisWeek": sum(1 for t in tasks if t.get("deadline") and today <= t["deadline"] <= end_week and t["status"] not in DONE_STATUSES),
        "unassigned": sum(1 for t in tasks if not (t.get("primaryOwner") or t.get("owner"))),
    }
    status_counts = {s: 0 for s in STATUSES}
    owner_status, owner_overdue, agency_load, weeks = {}, {}, {}, {}
    risk = {"Overdue": 0, "Due today": 0, "Due this week": 0, "No deadline": 0, "Later": 0}
    review_aging = {"0-2 days": 0, "3-6 days": 0, "7+ days": 0}
    agency_throughput, heatmap, planned_completed = {}, {}, {}
    for t in tasks:
        status = t["status"]
        owner = t.get("primaryOwner") or t.get("owner") or "Unassigned"
        agency = t.get("agency") or "Unassigned"
        status_counts[status] = status_counts.get(status, 0) + 1
        owner_status.setdefault(owner, {s: 0 for s in STATUSES})
        owner_status[owner][status] = owner_status[owner].get(status, 0) + 1
        agency_load[agency] = agency_load.get(agency, 0) + 1
        deadline = t.get("deadline") or ""
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
            week_key = time.strftime("%Y-W%W", time.strptime(deadline, "%Y-%m-%d"))
            weeks[week_key] = weeks.get(week_key, 0) + 1
            bucket = t.get("bucket") or t.get("zone") or "Unassigned"
            heatmap.setdefault(week_key, {})
            heatmap[week_key][bucket] = heatmap[week_key].get(bucket, 0) + 1
        if status == "In Review":
            age = t.get("risk", {}).get("stageAgeDays", 0)
            review_aging["0-2 days" if age <= 2 else "3-6 days" if age <= 6 else "7+ days"] += 1
        month = (deadline or t.get("completedAt") or t.get("updatedAt") or "")[:7]
        if month:
            planned_completed.setdefault(month, {"period": month, "planned": 0, "completed": 0, "published": 0})
            planned_completed[month]["planned"] += 1 if deadline else 0
            planned_completed[month]["completed"] += 1 if status == "Completed" else 0
            planned_completed[month]["published"] += 1 if status == "Published" else 0
        agency_throughput.setdefault(agency, {"agency": agency, "active": 0, "completed": 0, "published": 0, "stuck": 0})
        agency_throughput[agency]["active"] += 1 if status in ACTIVE_STATUSES else 0
        agency_throughput[agency]["completed"] += 1 if status == "Completed" else 0
        agency_throughput[agency]["published"] += 1 if status == "Published" else 0
        agency_throughput[agency]["stuck"] += 1 if t.get("risk", {}).get("stuck") else 0
    deadline_heatmap = [{"week": w, "bucket": b, "count": c} for w, buckets in sorted(heatmap.items())[:12] for b, c in sorted(buckets.items())]
    return {
        "cards": cards,
        "ownerWorkload": [{"owner": k, **v, "total": sum(v.values())} for k, v in sorted(owner_status.items(), key=lambda kv: -sum(kv[1].values()))],
        "ownerOverdue": [{"owner": k, "count": v} for k, v in sorted(owner_overdue.items(), key=lambda kv: -kv[1])],
        "upcomingWeeks": [{"week": k, "count": v} for k, v in sorted(weeks.items())[:10]],
        "deadlineRisk": [{"name": k, "count": v} for k, v in risk.items()],
        "statusDistribution": [{"status": k, "count": v} for k, v in status_counts.items()],
        "agencyLoad": [{"agency": k, "count": v} for k, v in sorted(agency_load.items(), key=lambda kv: -kv[1])],
        "productionFunnel": [{"status": s, "count": status_counts.get(s, 0)} for s in STATUSES],
        "deadlineHeatmap": deadline_heatmap,
        "reviewAging": [{"bucket": k, "count": v} for k, v in review_aging.items()],
        "agencyThroughput": sorted(agency_throughput.values(), key=lambda r: (-(r["active"] + r["completed"] + r["published"]), r["agency"])),
        "plannedVsCompleted": [planned_completed[k] for k in sorted(planned_completed)][-8:],
    }


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
    owner_scorecards, by_owner = [], {}
    for t in tasks:
        owner = t.get("primaryOwner") or t.get("owner") or "Unassigned"
        by_owner.setdefault(owner, {"owner": owner, "active": 0, "blocked": 0, "complete": 0, "total": 0})
        by_owner[owner]["total"] += 1
        by_owner[owner]["active"] += 1 if t["status"] in ACTIVE_STATUSES else 0
        by_owner[owner]["blocked"] += 1 if t["risk"]["missingDeadline"] or t["risk"]["missingOwner"] or t["risk"]["stuck"] or t["risk"]["overdue"] else 0
        by_owner[owner]["complete"] += 1 if t["status"] in DONE_STATUSES else 0
    owner_scorecards = sorted(by_owner.values(), key=lambda x: (-x["blocked"], -x["active"], -x["total"]))[:8]
    by_bucket = {}
    for t in tasks:
        bucket = t.get("bucket") or t.get("zone") or "Unassigned"
        by_bucket.setdefault(bucket, {"bucket": bucket, "admin": t.get("bucketAdmin") or "Unassigned", "total": 0, "active": 0, "missingPrimary": 0, "missingSecondary": 0, "missingDeadline": 0, "ready": 0})
        row = by_bucket[bucket]
        row["total"] += 1
        row["active"] += 1 if t["status"] in ACTIVE_STATUSES else 0
        row["missingPrimary"] += 1 if t["risk"]["missingPrimary"] else 0
        row["missingSecondary"] += 1 if t["risk"]["missingSecondary"] else 0
        row["missingDeadline"] += 1 if t["risk"]["missingDeadline"] else 0
        row["ready"] += 1 if t["status"] in ["Ready", "Completed"] else 0
    by_agency = {}
    for t in tasks:
        agency = t.get("agency") or "Unassigned"
        by_agency.setdefault(agency, {"agency": agency, "active": 0, "stuck": 0, "missingOwner": 0, "total": 0})
        by_agency[agency]["total"] += 1
        by_agency[agency]["active"] += 1 if t["status"] in ACTIVE_STATUSES else 0
        by_agency[agency]["stuck"] += 1 if t["risk"]["stuck"] else 0
        by_agency[agency]["missingOwner"] += 1 if t["risk"]["missingOwner"] else 0
    by_admin = {}
    for t in tasks:
        admin = t.get("bucketAdmin") or "Unassigned"
        by_admin.setdefault(admin, {"admin": admin, "buckets": set(), "total": 0, "needsAttention": 0, "active": 0})
        by_admin[admin]["buckets"].add(t.get("bucket") or t.get("zone") or "Unassigned")
        by_admin[admin]["total"] += 1
        by_admin[admin]["active"] += 1 if t["status"] in ACTIVE_STATUSES else 0
        by_admin[admin]["needsAttention"] += 1 if t["risk"]["missingPrimary"] or t["risk"]["missingSecondary"] or t["risk"]["missingDeadline"] or t["risk"]["stuck"] else 0
    admin_health = [{**v, "bucketCount": len(v["buckets"]), "buckets": sorted(v["buckets"])} for v in by_admin.values()]
    return {
        "cards": cards,
        "insights": [
            {"title": f"{cards['missingPrimary']} tasks need primary owners", "body": "Primary owner is directly accountable.", "quickFilter": "needs-owner", "tone": "red" if cards["missingPrimary"] else "green"},
            {"title": f"{cards['missingSecondary']} tasks need secondary owners", "body": "Backup owners keep work moving.", "quickFilter": "needs-secondary", "tone": "amber" if cards["missingSecondary"] else "green"},
            {"title": f"{cards['missingDeadline']} tasks need deadlines", "body": "Forecasting depends on expected dates.", "quickFilter": "needs-deadline", "tone": "amber" if cards["missingDeadline"] else "green"},
        ],
        "reviewBottlenecks": [t for t in tasks if t["status"] == "In Review"][:10],
        "readyToPublish": [t for t in tasks if t["status"] in ["Ready", "Completed"]][:10],
        "ownerScorecards": owner_scorecards,
        "agencyHealth": sorted(by_agency.values(), key=lambda x: (-x["active"], -x["total"])),
        "bucketHealth": sorted(by_bucket.values(), key=lambda x: (-x["missingPrimary"] - x["missingSecondary"] - x["missingDeadline"], -x["total"])),
        "adminHealth": sorted(admin_health, key=lambda x: (-x["needsAttention"], -x["active"], -x["total"])),
    }


def next_no(cur):
    cur.execute("SELECT COALESCE(MAX(no), 0) + 1 AS n FROM tasks")
    return int(cur.fetchone()["n"])


def ensure_task_checklist(cur, task_id):
    ts = now_iso()
    for step in CHECKLIST_STEPS:
        cur.execute('INSERT INTO task_checklists("taskId", step, "isDone", "updatedBy", "updatedAt") VALUES(%s,%s,FALSE,%s,%s) ON CONFLICT ("taskId", step) DO NOTHING', [task_id, step, "", ts])


def task_collaboration(cur, task_id):
    ensure_task_checklist(cur, task_id)
    cur.execute('SELECT task_comments.*, users."displayName", users.username FROM task_comments JOIN users ON users.id = task_comments."userId" WHERE "taskId" = %s ORDER BY task_comments.id DESC LIMIT 50', [task_id])
    comments = cur.fetchall()
    cur.execute('SELECT task_assets.*, users."displayName", users.username FROM task_assets JOIN users ON users.id = task_assets."userId" WHERE "taskId" = %s ORDER BY task_assets.id DESC LIMIT 50', [task_id])
    assets = cur.fetchall()
    cur.execute('SELECT approval_events.*, users."displayName", users.username FROM approval_events JOIN users ON users.id = approval_events."userId" WHERE "taskId" = %s ORDER BY approval_events.id DESC LIMIT 30', [task_id])
    approvals = cur.fetchall()
    cur.execute('SELECT * FROM task_checklists WHERE "taskId" = %s ORDER BY id', [task_id])
    checklist = cur.fetchall()
    cur.execute('SELECT * FROM activity_log WHERE "taskId" = %s ORDER BY id DESC LIMIT 20', [task_id])
    activity = cur.fetchall()
    return {"comments": comments, "assets": assets, "approvals": approvals, "checklist": checklist, "activity": activity}


def can_access_task(cur, user, task_id):
    if not user:
        return False
    if role_from_user(user) == "super_admin":
        cur.execute("SELECT 1 FROM tasks WHERE id = %s LIMIT 1", [task_id])
        return cur.fetchone() is not None
    clause, vals = visibility_clause(user)
    if not clause:
        cur.execute("SELECT 1 FROM tasks WHERE id = %s LIMIT 1", [task_id])
        return cur.fetchone() is not None
    cur.execute(f"SELECT 1 FROM tasks WHERE id = %s AND {clause} LIMIT 1", [task_id, *vals])
    return cur.fetchone() is not None


def log_activity(cur, task_id, action, actor, before, after):
    cur.execute('INSERT INTO activity_log("taskId",action,"actorRole","changedAt","beforeJson","afterJson") VALUES(%s,%s,%s,%s,%s,%s)', [task_id, action, actor, now_iso(), json.dumps(before or {}), json.dumps(after or {})])


def action_label(before, after, bulk=False):
    prefix = "bulk " if bulk else ""
    if before.get("status") != after.get("status"):
        return prefix + ("task published" if after.get("status") == "Published" else "task completed" if after.get("status") == "Completed" else "status changed")
    for key, label in [("primaryOwner", "primary owner"), ("secondaryOwner", "secondary owner"), ("bucketAdmin", "bucket admin"), ("deadline", "deadline"), ("priority", "priority")]:
        if before.get(key) != after.get(key):
            return prefix + f"{label} changed"
    return prefix + "task updated"


def canonical_person_name(cur, value):
    row = user_by_name(cur, value)
    return row["displayName"] if row else str(value or "").strip()


def canonicalize_task_people(cur, payload):
    for field in ["owner", "bucketAdmin", "primaryOwner", "secondaryOwner", "reviewer"]:
        if field in payload and payload.get(field):
            payload[field] = canonical_person_name(cur, payload.get(field))
    return payload


def access_matrix(cur):
    users = all_users(cur)
    rows = []
    for user in users:
        visible = query_tasks({}, user)
        rows.append({
            "user": user,
            "visibleTasks": len(visible),
            "canCreate": can_write(user["role"]),
            "canEdit": can_write(user["role"]),
            "canReview": can_review(user["role"]),
            "canImport": can_admin(user["role"]),
            "canDelete": can_admin(user["role"]),
            "canManageUsers": can_admin(user["role"]),
            "scope": user.get("access") or [{"accessType": "assigned", "accessValue": user["displayName"]}],
        })
    return rows


def digest_for_user(user):
    tasks = query_tasks({}, user)
    return digest_for_tasks(tasks)


def digest_for_tasks(tasks):
    today, end_week = today_date(), time.strftime("%Y-%m-%d", time.localtime(time.time() + 6 * 86400))
    due_today = [t for t in tasks if t.get("deadline") == today and t.get("status") not in DONE_STATUSES]
    due_soon = [t for t in tasks if t.get("deadline") and today < t["deadline"] <= end_week and t.get("status") not in DONE_STATUSES]
    overdue = [t for t in tasks if t.get("deadline") and t["deadline"] < today and t.get("status") not in DONE_STATUSES]
    review = [t for t in tasks if t.get("status") == "In Review"]
    ready = [t for t in tasks if t.get("status") in ["Ready", "Completed"]]
    blocked = [t for t in tasks if t.get("risk", {}).get("missingDeadline") or t.get("risk", {}).get("stuck") or t.get("risk", {}).get("overdue")]
    return {"dueToday": due_today[:20], "dueSoon": due_soon[:20], "overdue": overdue[:20], "waitingForReview": review[:20], "readyToPublish": ready[:20], "blocked": blocked[:20], "summary": {"dueToday": len(due_today), "dueSoon": len(due_soon), "overdue": len(overdue), "waitingForReview": len(review), "readyToPublish": len(ready), "blocked": len(blocked)}}


def deployment_status():
    return {"appUrl": APP_URL, "databasePath": "Postgres DATABASE_URL", "smtpConfigured": SMTP_CONFIGURED, "httpsReady": APP_URL.startswith("https://"), "backupScript": "scripts/export_sqlite_to_json.py", "migrationStyle": "Postgres schema in api/taskmaster.py", "checks": [{"label": "HTTPS/domain configured", "ok": APP_URL.startswith("https://")}, {"label": "Email provider configured", "ok": SMTP_CONFIGURED}, {"label": "Postgres DATABASE_URL set", "ok": bool(DATABASE_URL)}, {"label": "Aniket single super admin enforced", "ok": True}]}


def options_for(visible, cur):
    return {
        "brand": sorted({t.get("brand") for t in visible if t.get("brand")}),
        "bucket": sorted({t.get("bucket") for t in visible if t.get("bucket")}),
        "zone": sorted({t.get("zone") for t in visible if t.get("zone")}),
        "agency": sorted({t.get("agency") for t in visible if t.get("agency")}),
        "status": STATUSES,
        "owner": sorted({t.get("owner") for t in visible if t.get("owner")}),
        "bucketAdmin": sorted({t.get("bucketAdmin") for t in visible if t.get("bucketAdmin")}),
        "primaryOwner": sorted({t.get("primaryOwner") for t in visible if t.get("primaryOwner")}),
        "secondaryOwner": sorted({t.get("secondaryOwner") for t in visible if t.get("secondaryOwner")}),
        "reviewer": sorted({t.get("reviewer") for t in visible if t.get("reviewer")}),
        "priority": PRIORITIES,
        "roles": USER_ROLES,
        "assetTypes": ASSET_TYPES,
        "checklistSteps": CHECKLIST_STEPS,
        "users": all_users(cur),
    }


def planning_for(tasks):
    timeline = [t for t in tasks if t.get("plannedStart") or t.get("deadline") or t.get("publishDate")]
    return {
        "calendar": sorted(timeline, key=lambda t: t.get("deadline") or t.get("publishDate") or t.get("plannedStart") or "")[:80],
        "missingDates": [t for t in tasks if not t.get("deadline")][:80],
        "timeline": timeline[:120],
    }


def update_task(cur, task_id, changes, user):
    cur.execute("SELECT * FROM tasks WHERE id = %s", [task_id])
    before = cur.fetchone()
    if not before or not can_access_task(cur, user, task_id):
        return None, "Task not found."
    changes = canonicalize_task_people(cur, changes)
    merged = dict(before)
    merged.update(changes)
    task = normalize_task(merged, before)
    fields = ["no", *TASK_FIELDS[1:], "createdAt", "updatedAt", "completedAt", "lastStageChangedAt"]
    sets = ", ".join([f"{quote_ident(f)} = %s" for f in fields])
    cur.execute(f"UPDATE tasks SET {sets} WHERE id = %s", [task[f] for f in fields] + [task_id])
    return task, None


@app.middleware("http")
async def ensure_db(request: Request, call_next):
    if request.url.path.startswith("/api"):
        if request.url.path == "/api/me" and not request.cookies.get(SESSION_COOKIE, ""):
            return await call_next(request)
        db_error = require_database()
        if db_error:
            return db_error
    return await call_next(request)


@app.get("/api/me")
async def api_me(request: Request):
    return {"user": await current_user(request)}


@app.post("/api/auth/login")
async def api_login(request: Request):
    payload = await request.json()
    username = str(payload.get("username") or "").strip().lower()
    password = str(payload.get("password") or "")
    with conn() as db:
        with db.cursor() as cur:
            cur.execute('SELECT * FROM users WHERE username = %s AND "isActive" = TRUE', [username])
            row = cur.fetchone()
            if not row or not verify_password(password, row["passwordHash"]):
                return error("Invalid user ID or password.", 401)
            token = secrets.token_urlsafe(32)
            expires = int(time.time()) + SESSION_TTL_SECONDS
            cur.execute('DELETE FROM sessions WHERE "expiresAt" <= %s', [int(time.time())])
            cur.execute('INSERT INTO sessions(token,"userId","createdAt","expiresAt") VALUES(%s,%s,%s,%s)', [token, row["id"], now_iso(), expires])
            audit_event(cur, public_user(row), "login", "user", row["id"])
            db.commit()
    headers = {"Set-Cookie": f"{SESSION_COOKIE}={urllib.parse.quote(token)}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TTL_SECONDS}; Secure"}
    return json_response({"user": public_user(row)}, headers=headers)


@app.post("/api/auth/logout")
async def api_logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE, "")
    if token:
        with conn() as db:
            with db.cursor() as cur:
                cur.execute("DELETE FROM sessions WHERE token = %s", [token])
                db.commit()
    return json_response({"ok": True}, headers={"Set-Cookie": f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0; Secure"})


@app.post("/api/auth/request-reset")
async def api_request_reset(request: Request):
    payload = await request.json()
    username = str(payload.get("username") or "").strip().lower()
    with conn() as db:
        with db.cursor() as cur:
            cur.execute('SELECT * FROM users WHERE username = %s AND "isActive" = TRUE', [username])
            row = cur.fetchone()
            if row:
                token = secrets.token_urlsafe(32)
                cur.execute('INSERT INTO password_reset_tokens(token,"userId","createdAt","expiresAt","usedAt") VALUES(%s,%s,%s,%s,%s)', [token, row["id"], now_iso(), int(time.time()) + 3600, ""])
                notify_user(cur, row["id"], "", "Password reset requested", "Ask the super admin for reset if email is not configured.")
                audit_event(cur, public_user(row), "password_reset_requested", "user", row["id"], {"smtpConfigured": SMTP_CONFIGURED})
                db.commit()
                return {"ok": True, "emailConfigured": SMTP_CONFIGURED, "resetToken": token if not SMTP_CONFIGURED else ""}
    return {"ok": True, "emailConfigured": SMTP_CONFIGURED}


@app.post("/api/auth/reset-password")
async def api_reset_password(request: Request):
    payload = await request.json()
    token = str(payload.get("token") or "")
    new_password = str(payload.get("newPassword") or "")
    if len(new_password) < 8:
        return error("New password must be at least 8 characters.")
    with conn() as db:
        with db.cursor() as cur:
            cur.execute(
                'SELECT password_reset_tokens.*, users."displayName" FROM password_reset_tokens JOIN users ON users.id = password_reset_tokens."userId" WHERE token = %s AND "usedAt" = %s AND "expiresAt" > %s',
                [token, "", int(time.time())],
            )
            row = cur.fetchone()
            if not row:
                return error("Reset token is invalid or expired.")
            cur.execute('UPDATE users SET "passwordHash" = %s, "mustChangePassword" = FALSE, "updatedAt" = %s WHERE id = %s', [hash_password(new_password), now_iso(), row["userId"]])
            cur.execute('UPDATE password_reset_tokens SET "usedAt" = %s WHERE token = %s', [now_iso(), token])
            audit_event(cur, {"id": row["userId"], "displayName": row["displayName"]}, "password_reset_completed", "user", row["userId"])
            db.commit()
    return {"ok": True}


@app.api_route("/api/tasks/export.csv", methods=["GET"])
async def api_export(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    rows = query_tasks(dict(request.query_params), user)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=["id", *TASK_FIELDS, "createdAt", "updatedAt", "completedAt", "lastStageChangedAt"], extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return PlainTextResponse(stream.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=astral_video_tracker.csv"})


@app.get("/api/tasks")
async def api_tasks(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    return {"tasks": query_tasks(dict(request.query_params), user)}


@app.post("/api/tasks")
async def api_create_task(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_write(user["role"]):
        return error("Viewer role cannot create tasks.", 403)
    payload = await request.json()
    with conn() as db:
        with db.cursor() as cur:
            payload = canonicalize_task_people(cur, payload)
            payload["no"] = payload.get("no") or next_no(cur)
            task = normalize_task(payload)
            insert_task(cur, task)
            log_activity(cur, task["id"], "create", user["displayName"], {}, task)
            audit_event(cur, user, "task_created", "task", task["id"], {"title": task["title"]})
            db.commit()
    task["risk"] = task_risk(task)
    return json_response({"task": task}, 201)


@app.post("/api/tasks/import")
async def api_import_tasks(request: Request):
    try:
        user, fail = await require_user(request)
        if fail:
            return fail
        if not can_admin(user["role"]):
            return error("Only the super admin can import CSV.", 403)
        text = (await request.body()).decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        tasks = []
        for raw in reader:
            if not any((value or "").strip() for value in raw.values()):
                continue
            tasks.append(normalize_task(raw))
        if not tasks:
            return {"imported": 0}
        with conn() as db:
            with db.cursor() as cur:
                if request.query_params.get("replace") == "1":
                    for table in ["activity_log", "task_comments", "task_assets", "approval_events", "task_checklists", "tasks"]:
                        cur.execute(f"DELETE FROM {table}")
                fields = ["id", *TASK_FIELDS, "createdAt", "updatedAt", "completedAt", "lastStageChangedAt"]
                cols = ", ".join([quote_ident(f) for f in fields])
                updates = ", ".join([f"{quote_ident(f)} = EXCLUDED.{quote_ident(f)}" for f in fields if f != "id"])
                sql = f"INSERT INTO tasks({cols}) VALUES({qmarks(fields)}) ON CONFLICT (id) DO UPDATE SET {updates}"
                cur.executemany(sql, [[task.get(f, "") for f in fields] for task in tasks])
                checklist_rows = [(task["id"], step, False, "", now_iso()) for task in tasks for step in CHECKLIST_STEPS]
                cur.executemany(
                    'INSERT INTO task_checklists("taskId", step, "isDone", "updatedBy", "updatedAt") VALUES(%s,%s,%s,%s,%s) ON CONFLICT ("taskId", step) DO NOTHING',
                    checklist_rows,
                )
                audit_event(cur, user, "tasks_imported", "task", "", {"count": len(tasks)})
                db.commit()
        return {"imported": len(tasks)}
    except Exception as exc:
        return error(f"Import failed: {exc}", 500)


@app.post("/api/tasks/reset")
async def api_reset_tasks(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_admin(user["role"]):
        return error("Only the super admin can reset tasks.", 403)
    with conn() as db:
        with db.cursor() as cur:
            for table in ["tasks", "activity_log", "task_comments", "task_assets", "approval_events", "task_checklists"]:
                cur.execute(f"DELETE FROM {table}")
            seed_tasks(cur)
            audit_event(cur, user, "tasks_reset", "task", "", {})
            db.commit()
    return {"ok": True}


@app.get("/api/analytics")
async def api_analytics(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    return analytics_for(query_tasks(dict(request.query_params), user))


@app.get("/api/analytics/command-center")
async def api_command(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    return command_center_for(query_tasks(dict(request.query_params), user))


@app.get("/api/bootstrap")
async def api_bootstrap(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    params = dict(request.query_params)
    tasks = query_tasks(params, user)
    name = user["displayName"]
    mine = [t for t in tasks if name in [t.get("primaryOwner"), t.get("secondaryOwner"), t.get("bucketAdmin"), t.get("reviewer"), t.get("owner")]]
    payload = {
        "tasks": {"tasks": tasks},
        "analytics": analytics_for(tasks),
        "command": command_center_for(tasks),
        "myWork": {"tasks": mine, "counts": analytics_for(mine)["cards"]},
        "planning": planning_for(tasks),
        "digest": digest_for_tasks(tasks),
        "notifications": {"notifications": []},
        "users": {"users": []},
        "accessMatrix": {"matrix": []},
        "deployment": None,
        "audit": {"events": []},
    }
    with conn() as db:
        with db.cursor() as cur:
            payload["options"] = options_for(tasks, cur)
            cur.execute('SELECT * FROM notifications WHERE "userId" = %s ORDER BY "isRead" ASC, id DESC LIMIT 80', [user["id"]])
            payload["notifications"] = {"notifications": cur.fetchall()}
            if can_admin(user["role"]) and params.get("view") == "admin":
                payload["users"] = {"users": all_users(cur)}
                payload["accessMatrix"] = {"matrix": access_matrix(cur)}
                payload["deployment"] = deployment_status()
                cur.execute("SELECT * FROM system_audit ORDER BY id DESC LIMIT 120")
                payload["audit"] = {"events": cur.fetchall()}
    return payload


@app.get("/api/options")
async def api_options(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    visible = query_tasks({}, user)
    with conn() as db:
        with db.cursor() as cur:
            return options_for(visible, cur)


@app.get("/api/users")
async def api_users(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_admin(user["role"]):
        return error("Only the super admin can manage users.", 403)
    with conn() as db:
        with db.cursor() as cur:
            try:
                return {"users": all_users(cur)}
            except Exception as exc:
                return error(f"Could not load users: {exc}", 500)


@app.post("/api/users")
async def api_create_user(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_admin(user["role"]):
        return error("Only the super admin can create users.", 403)
    payload = await request.json()
    username = str(payload.get("username") or "").strip().lower()
    display = str(payload.get("displayName") or username).strip()
    role = str(payload.get("role") or "editor")
    if not username or role not in USER_ROLES:
        return error("Valid username and role are required.")
    if role == "super_admin" and username != "aniket":
        return error("Aniket is the single super admin.")
    with conn() as db:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(%s) OR LOWER(\"displayName\") = LOWER(%s)", [username, display])
            if cur.fetchone():
                return error("User ID or display name already exists.")
            ts = now_iso()
            user_id = f"user_{username}"
            cur.execute(
                'INSERT INTO users(id,username,"displayName",role,email,phone,team,"agencyName","isAgencyUser","notificationPrefs","passwordHash","isActive","mustChangePassword","createdAt","updatedAt") VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,TRUE,%s,%s)',
                [user_id, username, display, role, payload.get("email", ""), payload.get("phone", ""), payload.get("team", ""), payload.get("agencyName", ""), bool(payload.get("isAgencyUser") or role == "agency"), json.dumps(payload.get("notificationPrefs") or {}), hash_password(payload.get("password") or INITIAL_PASSWORD), ts, ts],
            )
            for item in payload.get("access") or []:
                if item.get("accessType") and item.get("accessValue"):
                    cur.execute('INSERT INTO user_access("userId","accessType","accessValue") VALUES(%s,%s,%s) ON CONFLICT DO NOTHING', [user_id, item["accessType"], item["accessValue"]])
            audit_event(cur, user, "user_created", "user", user_id, {"role": role})
            db.commit()
            return json_response({"users": all_users(cur)}, 201)


@app.patch("/api/users/{user_id}")
async def api_patch_user(user_id: str, request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_admin(user["role"]):
        return error("Only the super admin can update users.", 403)
    payload = await request.json()
    allowed = {}
    for field in ["displayName", "email", "phone", "team", "agencyName"]:
        if field in payload:
            allowed[field] = str(payload.get(field) or "").strip()
    if "role" in payload:
        role = str(payload["role"])
        if role not in USER_ROLES:
            return error("Invalid role.")
        if role == "super_admin" and user_id != "user_aniket":
            return error("Aniket is the single super admin.")
        allowed["role"] = role
    if "isActive" in payload:
        allowed["isActive"] = bool(payload["isActive"])
    if "isAgencyUser" in payload:
        allowed["isAgencyUser"] = bool(payload["isAgencyUser"])
    if "notificationPrefs" in payload:
        allowed["notificationPrefs"] = json.dumps(payload.get("notificationPrefs") or {})
    if payload.get("password"):
        allowed["passwordHash"] = hash_password(str(payload["password"]))
        allowed["mustChangePassword"] = True
    if not allowed and "access" not in payload:
        return error("No user changes supplied.")
    allowed["updatedAt"] = now_iso()
    with conn() as db:
        with db.cursor() as cur:
            if "displayName" in allowed:
                cur.execute('SELECT id FROM users WHERE LOWER("displayName") = LOWER(%s) AND id != %s', [allowed["displayName"], user_id])
                if cur.fetchone():
                    return error("That display name already exists. Use unique names to protect owner analytics.")
            if "role" in allowed and user_id == "user_aniket":
                cur.execute("UPDATE users SET role = 'admin' WHERE role = 'super_admin' AND id != 'user_aniket'")
            if allowed:
                sets = ", ".join([f"{quote_ident(k)} = %s" for k in allowed])
                cur.execute(f"UPDATE users SET {sets} WHERE id = %s", [*allowed.values(), user_id])
            cur.execute("UPDATE users SET role = 'super_admin', \"isActive\" = TRUE WHERE id = 'user_aniket'")
            if "access" in payload:
                cur.execute('DELETE FROM user_access WHERE "userId" = %s', [user_id])
                for item in payload.get("access") or []:
                    if item.get("accessType") and item.get("accessValue"):
                        cur.execute('INSERT INTO user_access("userId","accessType","accessValue") VALUES(%s,%s,%s) ON CONFLICT DO NOTHING', [user_id, item["accessType"], item["accessValue"]])
            audit_event(cur, user, "user_updated", "user", user_id, {"fields": sorted(allowed.keys())})
            db.commit()
            return {"users": all_users(cur)}


@app.get("/api/admin/access-matrix")
async def api_access_matrix(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_admin(user["role"]):
        return error("Only the super admin can view the access matrix.", 403)
    with conn() as db:
        with db.cursor() as cur:
            return {"matrix": access_matrix(cur)}


@app.get("/api/admin/audit")
async def api_audit(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_admin(user["role"]):
        return error("Only the super admin can view audit events.", 403)
    with conn() as db:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM system_audit ORDER BY id DESC LIMIT 120")
            return {"events": cur.fetchall()}


@app.get("/api/activity")
async def api_activity(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    task_id = request.query_params.get("taskId", "")
    with conn() as db:
        with db.cursor() as cur:
            if not can_access_task(cur, user, task_id):
                return error("Task not found.", 404)
            cur.execute('SELECT * FROM activity_log WHERE "taskId" = %s ORDER BY id DESC LIMIT 30', [task_id])
            return {"activity": cur.fetchall()}


@app.get("/api/settings/deployment")
async def api_deployment(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_admin(user["role"]):
        return error("Only the super admin can view deployment settings.", 403)
    return deployment_status()


@app.get("/api/my-work")
async def api_my_work(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    name = user["displayName"]
    mine = [t for t in query_tasks(dict(request.query_params), user) if name in [t.get("primaryOwner"), t.get("secondaryOwner"), t.get("bucketAdmin"), t.get("reviewer"), t.get("owner")]]
    return {"tasks": mine, "counts": analytics_for(mine)["cards"]}


@app.get("/api/planning")
async def api_planning(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    tasks = query_tasks(dict(request.query_params), user)
    timeline = [t for t in tasks if t.get("plannedStart") or t.get("deadline") or t.get("publishDate")]
    return {"calendar": sorted(timeline, key=lambda t: t.get("deadline") or t.get("publishDate") or t.get("plannedStart") or "")[:80], "missingDates": [t for t in tasks if not t.get("deadline")][:80], "timeline": timeline[:120]}


@app.get("/api/notifications")
async def api_notifications(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    with conn() as db:
        with db.cursor() as cur:
            cur.execute('SELECT * FROM notifications WHERE "userId" = %s ORDER BY "isRead" ASC, id DESC LIMIT 80', [user["id"]])
            return {"notifications": cur.fetchall()}


@app.get("/api/notifications/digest")
async def api_digest(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    return digest_for_user(user)


@app.patch("/api/notifications/{notif_id}")
async def api_read_notification(notif_id: str, request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    with conn() as db:
        with db.cursor() as cur:
            cur.execute('UPDATE notifications SET "isRead" = TRUE WHERE id = %s AND "userId" = %s', [notif_id, user["id"]])
            db.commit()
    return {"ok": True}


@app.get("/api/tasks/{task_id}/collaboration")
async def api_collaboration(task_id: str, request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    with conn() as db:
        with db.cursor() as cur:
            if not can_access_task(cur, user, task_id):
                return error("Task not found.", 404)
            return task_collaboration(cur, task_id)


@app.post("/api/tasks/{task_id}/comments")
async def api_comment(task_id: str, request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_collaborate(user["role"]):
        return error("Your role cannot comment.", 403)
    payload = await request.json()
    body = str(payload.get("body") or "").strip()
    if not body:
        return error("Comment cannot be empty.")
    with conn() as db:
        with db.cursor() as cur:
            if not can_access_task(cur, user, task_id):
                return error("Task not found.", 404)
            cur.execute('INSERT INTO task_comments("taskId","userId",body,"createdAt") VALUES(%s,%s,%s,%s)', [task_id, user["id"], body, now_iso()])
            log_activity(cur, task_id, "comment added", user["displayName"], {}, {"body": body})
            for mention in set(re.findall(r"@([A-Za-z0-9_]+)", body)):
                target = user_by_name(cur, mention)
                if target and target["id"] != user["id"]:
                    notify_user(cur, target["id"], task_id, f"{user['displayName']} mentioned you", body[:120])
            db.commit()
            return json_response(task_collaboration(cur, task_id), 201)


@app.post("/api/tasks/{task_id}/assets")
async def api_asset(task_id: str, request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_collaborate(user["role"]):
        return error("Your role cannot add assets.", 403)
    payload = await request.json()
    asset_type = payload.get("assetType") if payload.get("assetType") in ASSET_TYPES else "Other"
    label, url = str(payload.get("label") or asset_type).strip(), str(payload.get("url") or "").strip()
    if not url:
        return error("Asset URL is required.")
    with conn() as db:
        with db.cursor() as cur:
            if not can_access_task(cur, user, task_id):
                return error("Task not found.", 404)
            cur.execute('INSERT INTO task_assets("taskId","userId","assetType",label,url,"createdAt") VALUES(%s,%s,%s,%s,%s,%s)', [task_id, user["id"], asset_type, label, url, now_iso()])
            log_activity(cur, task_id, "asset added", user["displayName"], {}, {"assetType": asset_type, "label": label, "url": url})
            db.commit()
            return json_response(task_collaboration(cur, task_id), 201)


@app.post("/api/tasks/{task_id}/review")
async def api_review(task_id: str, request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_review(user["role"]):
        return error("Your role cannot review tasks.", 403)
    payload = await request.json()
    decision = str(payload.get("decision") or "")
    if decision not in ["approved", "changes_requested", "ready", "published"]:
        return error("Invalid review decision.")
    status_by_decision = {"approved": "Ready", "changes_requested": "In Review", "ready": "Ready", "published": "Published"}
    changes = {"status": status_by_decision[decision]}
    if decision == "published":
        changes["publishDate"] = today_date()
    with conn() as db:
        with db.cursor() as cur:
            task, message = update_task(cur, task_id, changes, user)
            if message:
                return error(message, 404)
            cur.execute('INSERT INTO approval_events("taskId","userId",decision,note,"createdAt") VALUES(%s,%s,%s,%s,%s)', [task_id, user["id"], decision, str(payload.get("note") or ""), now_iso()])
            log_activity(cur, task_id, f"review {decision}", user["displayName"], {}, task)
            audit_event(cur, user, f"review_{decision}", "task", task_id, {"title": task["title"]})
            db.commit()
            return {"task": {**task, "risk": task_risk(task)}, **task_collaboration(cur, task_id)}


@app.post("/api/tasks/{task_id}/checklist")
async def api_checklist(task_id: str, request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_collaborate(user["role"]):
        return error("Your role cannot update checklists.", 403)
    payload = await request.json()
    step = str(payload.get("step") or "")
    if step not in CHECKLIST_STEPS:
        return error("Invalid checklist step.")
    with conn() as db:
        with db.cursor() as cur:
            if not can_access_task(cur, user, task_id):
                return error("Task not found.", 404)
            ensure_task_checklist(cur, task_id)
            cur.execute('UPDATE task_checklists SET "isDone" = %s, "updatedBy" = %s, "updatedAt" = %s WHERE "taskId" = %s AND step = %s', [bool(payload.get("isDone")), user["displayName"], now_iso(), task_id, step])
            log_activity(cur, task_id, f"checklist {step}", user["displayName"], {}, {"step": step, "isDone": bool(payload.get("isDone"))})
            db.commit()
            return task_collaboration(cur, task_id)


@app.patch("/api/tasks/bulk")
async def api_bulk(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_write(user["role"]):
        return error("Viewer role cannot bulk edit tasks.", 403)
    payload = await request.json()
    ids, changes = payload.get("ids") or [], {k: v for k, v in (payload.get("changes") or {}).items() if k in set(TASK_FIELDS)}
    if not ids or not changes:
        return error("Bulk edit requires ids and editable changes.")
    updated = []
    with conn() as db:
        with db.cursor() as cur:
            for task_id in ids:
                task, message = update_task(cur, task_id, dict(changes), user)
                if task:
                    updated.append({**task, "risk": task_risk(task)})
                    log_activity(cur, task_id, "bulk task updated", user["displayName"], {}, task)
            audit_event(cur, user, "tasks_bulk_updated", "task", "", {"count": len(updated), "fields": sorted(changes.keys())})
            db.commit()
    return {"updated": len(updated), "tasks": updated}


@app.patch("/api/tasks/{task_id}")
async def api_patch_task(task_id: str, request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_write(user["role"]):
        return error("Viewer role cannot edit tasks.", 403)
    payload = await request.json()
    changes = {k: v for k, v in payload.items() if k in set(TASK_FIELDS)}
    if not changes:
        return error("No editable fields supplied.")
    with conn() as db:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM tasks WHERE id = %s", [task_id])
            before = cur.fetchone()
            task, message = update_task(cur, task_id, changes, user)
            if message:
                return error(message, 404)
            log_activity(cur, task_id, action_label(before or {}, task), user["displayName"], before or {}, task)
            audit_event(cur, user, "task_updated", "task", task_id, {"fields": sorted(changes.keys())})
            db.commit()
    return {"task": {**task, "risk": task_risk(task)}}


@app.delete("/api/tasks/{task_id}")
async def api_delete_task(task_id: str, request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    if not can_admin(user["role"]):
        return error("Only the super admin can delete tasks.", 403)
    with conn() as db:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM tasks WHERE id = %s", [task_id])
            before = cur.fetchone()
            if not before:
                return error("Task not found.", 404)
            cur.execute("DELETE FROM tasks WHERE id = %s", [task_id])
            log_activity(cur, task_id, "delete", user["displayName"], before, {})
            audit_event(cur, user, "task_deleted", "task", task_id, {"title": before["title"]})
            db.commit()
    return {"ok": True}


@app.patch("/api/me/password")
async def api_change_password(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    payload = await request.json()
    new_password = str(payload.get("newPassword") or "")
    if len(new_password) < 8:
        return error("New password must be at least 8 characters.")
    with conn() as db:
        with db.cursor() as cur:
            cur.execute('SELECT * FROM users WHERE id = %s AND "isActive" = TRUE', [user["id"]])
            row = cur.fetchone()
            if not row or not verify_password(str(payload.get("currentPassword") or ""), row["passwordHash"]):
                return error("Current password is incorrect.")
            cur.execute('UPDATE users SET "passwordHash" = %s, "mustChangePassword" = FALSE, "updatedAt" = %s WHERE id = %s', [hash_password(new_password), now_iso(), user["id"]])
            cur.execute("SELECT * FROM users WHERE id = %s", [user["id"]])
            refreshed = public_user(cur.fetchone())
            db.commit()
    return {"user": refreshed}


@app.patch("/api/me/preferences")
async def api_preferences(request: Request):
    user, fail = await require_user(request)
    if fail:
        return fail
    payload = await request.json()
    prefs = payload.get("notificationPrefs") or {}
    with conn() as db:
        with db.cursor() as cur:
            cur.execute('UPDATE users SET "notificationPrefs" = %s, "updatedAt" = %s WHERE id = %s', [json.dumps(prefs), now_iso(), user["id"]])
            cur.execute("SELECT * FROM users WHERE id = %s", [user["id"]])
            refreshed = public_user(cur.fetchone())
            db.commit()
    return {"user": refreshed}


@app.get("/")
async def static_index():
    return FileResponse(PUBLIC_DIR / "index.html")


@app.get("/{asset_path:path}")
async def static_asset(asset_path: str):
    if asset_path.startswith("api/"):
        return error("Not found.", 404)
    target = (PUBLIC_DIR / asset_path).resolve()
    try:
        target.relative_to(PUBLIC_DIR.resolve())
    except ValueError:
        return error("Not found.", 404)
    if not target.exists() or target.is_dir():
        return error("Not found.", 404)
    return FileResponse(target)
