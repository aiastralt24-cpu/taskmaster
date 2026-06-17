# Taskmaster Vercel Deployment Checklist

Use this before giving Taskmaster to a wider internal or agency team.

## Target Architecture

- Vercel static frontend from `public/`.
- Vercel Python serverless API from `api/index.py`.
- Neon Postgres as production data store through `DATABASE_URL`.
- Local SQLite remains private and is used only for local development or one-time data export.

## Required Vercel Environment

- `DATABASE_URL`: Neon Postgres pooled connection string.
- `TASKMASTER_APP_URL`: final HTTPS URL.
- `SESSION_SECRET`: long random value for future signing/rotation compatibility.
- `TASKMASTER_INITIAL_PASSWORD`: temporary password for first seeded users.
- `SMTP_HOST` and `SMTP_FROM`: required before email reset/digest delivery is considered configured.
- Optional SMTP credentials: `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`.

## GitHub And Vercel Setup

1. Push latest `main` to `aiastralt24-cpu/taskmaster`.
2. Import the repo into Vercel.
3. Add Neon Postgres from Vercel Marketplace.
4. Confirm `DATABASE_URL` is available in Preview and Production.
5. Set `TASKMASTER_APP_URL` separately for Preview and Production when possible.

## One-Time Data Migration

Do not commit the export file. It is ignored by Git.

```bash
python3 scripts/export_sqlite_to_json.py
vercel env pull .env.production.local
set -a; source .env.production.local; set +a
python3 scripts/import_json_to_postgres.py
```

The export/import flow excludes `sessions` and `password_reset_tokens`.

## Preview Verification

- Login works for `aniket`.
- Aniket is the only `super_admin`.
- Dashboard loads with the expected task count.
- Command, My Work, Planning, Board, Table, Reports, and Admin render.
- Table/board edits persist after refresh.
- Access Matrix loads and scoped visibility works for Jay/Yogen/Vaibhav/agency-style users.
- CSV export works.
- CSV import is available only to super admin.
- Password reset token flow works when SMTP is absent.
- Email-ready reset flow is enabled when SMTP env exists.

## Production Cutover

- Promote only after preview verification.
- Rotate temporary passwords for all real users.
- Confirm live SQLite and JSON exports are not committed.
- Confirm HTTPS domain is active.
- Confirm `TASKMASTER_APP_URL` matches production URL.
- Take a fresh local SQLite backup before import.
- Schedule regular Neon backups or exports.

## Operating Rules

- `Completed` means production output is done.
- `Ready` means approved and ready to publish.
- `Published` means live.
- Expected completion dates should be filled before deadline analytics are trusted.
