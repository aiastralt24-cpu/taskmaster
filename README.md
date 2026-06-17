# Astral Taskmaster

Production command-center tracker for Astral video/content operations.

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
