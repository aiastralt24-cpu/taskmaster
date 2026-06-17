# Astral Taskmaster

Production command-center tracker for Astral video/content operations.

## Production Architecture

Taskmaster is prepared for Vercel as:

- `public/` static frontend
- `api/index.py` FastAPI serverless API
- Neon Postgres via `DATABASE_URL`
- local SQLite only for local/offline development and one-time production import

## Run Locally

```bash
python3 server.py
```

Open:

```text
http://127.0.0.1:3401
```

## Default Users

Seeded users are created by `server.py` on startup:

- `aniket` - super admin
- `jay` - admin
- `yogen` - admin
- `vaibhav` - editor
- `akash` - editor
- `arvind` - editor

Initial password:

```text
Taskmaster@2026
```

Change passwords after first login.

## Data And Backups

The live SQLite database is intentionally ignored by Git because it contains auth/session/reset-token state.

Create a backup:

```bash
bash scripts/backup_taskmaster.sh
```

Review [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) before hosting.

## Deploy To Vercel

1. Connect GitHub repo `aiastralt24-cpu/taskmaster` to Vercel.
2. Add Neon Postgres from the Vercel Marketplace.
3. Set Vercel environment variables:
   - `DATABASE_URL`
   - `TASKMASTER_APP_URL`
   - `SESSION_SECRET`
   - `TASKMASTER_INITIAL_PASSWORD`
   - optional `SMTP_HOST`, `SMTP_FROM`, `SMTP_USER`, `SMTP_PASSWORD`
4. Export local SQLite data:

```bash
python3 scripts/export_sqlite_to_json.py
```

5. Pull production env locally and import once:

```bash
vercel env pull .env.production.local
set -a; source .env.production.local; set +a
python3 scripts/import_json_to_postgres.py
```

6. Deploy a Vercel preview, verify login and edits, then promote to production.
