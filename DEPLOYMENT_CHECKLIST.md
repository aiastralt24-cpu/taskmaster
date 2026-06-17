# Taskmaster Deployment Checklist

Use this before giving Taskmaster to a wider internal or agency team.

## Required Environment
- `TASKMASTER_APP_URL`: public app URL, preferably HTTPS.
- `TASKMASTER_DB_PATH`: absolute path to the production SQLite database.
- `TASKMASTER_BACKUP_DIR`: folder for scheduled database backups.
- `SMTP_HOST` and `SMTP_FROM`: required before email reset/digest delivery is treated as configured.

## Pre-Launch
- Run `scripts/backup_taskmaster.sh` and verify the backup opens with `sqlite3`.
- Confirm Aniket is the only `super_admin`.
- Rotate temporary passwords for all real users.
- Confirm agency users have `agency` role or `isAgencyUser` enabled and an `agencyName`.
- Confirm admins have bucket/agency access scopes where needed.
- Test CSV export and import on a copied database.

## Launch Checks
- App served over HTTPS.
- Domain points to the hosted app.
- Database backup job scheduled.
- Email provider configured or password reset handled by super admin only.
- Admin Access Matrix reviewed.
- Test login for one admin, one editor, one reviewer, one agency user, and one viewer.

## Operating Rules
- `Completed` means production output is done.
- `Ready` means approved and ready to publish.
- `Published` means live.
- Expected completion dates should be filled before deadline analytics are trusted.
