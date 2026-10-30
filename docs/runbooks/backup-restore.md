# Backup and restore

The app keeps its data in two files in the project folder: `db.sqlite3` (everything) and
`payroll.sqlite3` (approved hours for payroll). They belong together: **always back up and
restore both, from the same moment**. Neither file is ever committed to Git.

## Back up

```bash
uv run python manage.py backup_db          # or: make backup
```
- Writes `backups/db-<stamp>.sqlite3` and `backups/payroll-<stamp>.sqlite3` with the same
  timestamp, e.g. `db-20261024-120953.sqlite3`
  ([D-72](../decisions/D-072-backup-db-copies-both-databases-with-sqlite.md)).
- Uses SQLite's online backup, so it is **safe while the app is running**.
- `--dir <folder>` writes the copies somewhere else.
- `backups/` is not in Git: copy it somewhere safe (an external drive, a company share).

Back up before every update (`git pull`), before rebuilding demo data and regularly in daily use.

## Restore

1. Stop the server (Control + C).
2. Keep the current files until you have checked the result, e.g.:
   ```bash
   mv db.sqlite3 db-old.sqlite3
   mv payroll.sqlite3 payroll-old.sqlite3
   ```
3. Pick **one** timestamp and copy **both** files back:
   ```bash
   cp backups/db-20261024-120953.sqlite3 db.sqlite3
   cp backups/payroll-20261024-120953.sqlite3 payroll.sqlite3
   ```
4. Start the server, then repair anything approved after that backup:
   ```bash
   uv run python manage.py sync_payroll
   ```
   It publishes missing payroll records, supersedes stale ones and creates missing adjustments
   and registers; it is safe to repeat ([D-125](../decisions/D-125-audit-and-sync.md)).

## Why both files from the same time

Payroll records are copies of approvals in the main database. A main database from Monday with a
payroll database from Friday would show payroll records for approvals that no longer exist (or the
other way round). `sync_payroll` repairs what is *missing* from payroll, but payroll records are
append-only and are never deleted ([D-15](../decisions/D-015-append-only-means-snapshot-and-hours-fields.md)).

## Start over

Never delete the databases. To start again with fresh demo data, **move** them aside — see
[demo data → Start over](demo-data.md#start-over-with-fresh-demo-data).
