# D-72: backup_db copies both databases with SQLite's online backup API through a separate…

- **Status:** Accepted
- **Area:** Ops
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Ops** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: D.2, D.3.

## Decision

`backup_db` copies both databases with SQLite's online backup API through a separate read-only connection (safe while the app runs) to `backups/db-YYYYmmdd-HHMMSS.sqlite3` and `backups/payroll-…` with the same timestamp; `--dir` chooses another folder.

## Consequences

- **Checked by:** [T-113](../testing.md#t-113)
- **Cited in code:** [`apps/directory/management/commands/backup_db.py`](../../apps/directory/management/commands/backup_db.py)
