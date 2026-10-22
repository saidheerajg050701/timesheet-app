# Timesheet App — instructions for Claude Code

## Source of truth
- The full spec is docs/BUILD_GUIDE.md (Part B, including B.11 testing). Follow it exactly.
  If something is unclear, ask me before guessing.
- Build only the phase I ask for (Part C.4). Stop when that phase is done.

## Stack (do not substitute without asking)
Python 3.13 via uv; Django 5.2 LTS; two SQLite databases (default = db.sqlite3, payroll = payroll.sqlite3)
with a database router for the payroll app; django-environ; argon2-cffi (Argon2 password hashing);
django-axes; django-import-export; Faker; Django templates + Bootstrap 5 + HTMX + Chart.js
(vendored in static/vendor, no JS build step); pytest, pytest-django, factory_boy, time-machine,
pytest-cov, Playwright for Python; Ruff. Notifications are OUT of scope for version 1.

## Conventions
- Apps: directory, timesheets, audit, payroll, analytics. Settings package: config.
- Business rules live in <app>/services/*.py as plain, tested functions. Views stay thin.
- Every view enforces permissions server-side via directory/services/permissions.py.
- Payroll models live only in the payroll database; no foreign keys across databases; payroll
  records are append-only (supersede, never edit). publish_period must be idempotent.
- Passwords: Argon2 first in PASSWORD_HASHERS; never log, print or store plain passwords.
- Durations are integer minutes; work dates are DateField; deadlines computed in COMPANY_TZ.
- Use TextChoices for all statuses. Every manager/admin/payroll action writes an AuditLog row.
- Tests: follow docs/BUILD_GUIDE.md B.11 (layout, test IDs T-01…T-42, factories, fixed clock).
  Every new rule gets tests in the same phase. Name tests so the T-number is in the docstring.
- Never commit .env, db.sqlite3 or payroll.sqlite3. Keep .env.example up to date.
- Always run Python through uv (`uv run ...`); add packages with `uv add`, never pip.

## Commands
- uv run python manage.py runserver                       # http://127.0.0.1:8000
- uv run python manage.py migrate && uv run python manage.py migrate --database=payroll
- uv run python manage.py seed_demo
- uv run pytest -m "not e2e"                              # fast tests
- bash scripts/test_all.sh                                # everything (lint, checks, coverage, e2e)
- uv run python manage.py backup_db

## Definition of done for each phase
1. `bash scripts/test_all.sh` passes (once it exists; before that: ruff + pytest).
2. The server starts without errors.
3. Summarize what changed, list the new test IDs, and give me exact browser steps to verify.
4. Never delete or flush db.sqlite3 or payroll.sqlite3, or squash/delete migrations, without asking me.
