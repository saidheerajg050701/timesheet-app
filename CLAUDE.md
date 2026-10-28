# Timesheet App — instructions for Claude Code

## Source of truth
- The full spec is docs/BUILD_GUIDE.md (Part B, including B.11 testing). Follow it exactly.
  If something is unclear, ask me before guessing.
- If docs/BUILD_GUIDE.md B.12 conflicts with anything else, B.12 wins.
- Build only the phase I ask for (Part C.4). Stop when that phase is done.

## Stack (do not substitute without asking)
Python 3.13 via uv; Django 5.2 LTS; two SQLite databases (default = db.sqlite3, payroll = payroll.sqlite3)
with a database router for the payroll app; django-environ; argon2-cffi (Argon2 password hashing);
django-axes; Faker; Django templates + Bootstrap 5 + HTMX + Chart.js
(vendored in static/vendor, no JS build step); pytest, pytest-django, factory_boy, time-machine,
pytest-cov, Playwright for Python; Ruff. Notifications are OUT of scope for version 1.

## Conventions
- Apps: directory, timesheets, audit, payroll, analytics. Settings package: config.
- Every app uses a services package: <app>/services/<module>.py (e.g. payroll/services/publish.py,
  analytics/services/metrics.py); never a single services.py. Business rules live there as plain,
  tested functions. Views stay thin.
- Every view enforces permissions server-side via directory/services/permissions.py.
- Payroll models live only in the payroll database; no foreign keys across databases; payroll
  records are append-only as defined in B.12 D-15 (supersede, never edit). publish_period must be idempotent.
- Pay period registers (D-132–D-138): OPEN/READY are worked out live; only "Finalize & export"
  (payroll/services/register.py → finalize) creates a batch and saves the frozen register and
  lines; all register numbers come from PayrollWeek/PayrollAdjustment records. "Who must be
  approved" is approvals.must_be_approved, nowhere else. A register is READY only when everyone
  is approved (D-142). When an approver may approve / reject / edit is
  approvals.decision_blockers / edit_blockers only (Change 9, D-139–D-141); an edit from
  Approvals never sets submitted_at (that keeps "not submitted by employee" and MISSED).
- Passwords: Argon2 first in PASSWORD_HASHERS; never log, print or store plain passwords.
- Durations are integer minutes; work dates are DateField; deadlines computed in COMPANY_TZ.
- Weeks run Sunday–Saturday and are identified by their Sunday; pay periods start on the Sunday
  PAY_PERIOD_ANCHOR (D-111, D-113). Use timesheets/services/calendar.py, never weekday() arithmetic.
- Weekly grid row actions (change project/category, delete row) only rewrite the week as typed
  through timesheets/services/grid_rows.py and re-draw the grid; nothing is saved until the week is
  saved through save_week / edit_directly, where every entry rule and the audit live (D-129, D-130).
- Use TextChoices for all statuses. Every manager/admin/payroll action writes an AuditLog row
  (system actions use system_actor instead of actor, D-14).
- Project work is booked to a project and a task (D-148–D-152): the task rule lives only in
  timesheets/services/validation.py with timesheets/services/tasks.py; the charge code
  "<project>-<task>" is computed by tasks.charge_code, never stored. Payroll never sees tasks.
- Tests: follow docs/BUILD_GUIDE.md B.11 (layout, test IDs T-01 onward, factories, fixed clock).
  Every new rule gets tests in the same phase. New catalogued tests continue at T-43 and are added
  to the B.11 table (D-16). Each catalogued test's docstring starts with its ID (D-17).
- Never commit .env, db.sqlite3 or payroll.sqlite3. Keep .env.example up to date; if you change
  its DJANGO_SECRET_KEY or DEMO_PASSWORD example values, update directory/checks.py and seed_demo
  (they refuse those values, D-145, D-146; T-225/T-226 check they match).
- Always run Python through uv (`uv run ...`); add packages with `uv add`, never pip.

## Commands
- uv run python manage.py runserver                       # http://127.0.0.1:8000
- uv run python manage.py migrate && uv run python manage.py migrate --database=payroll
- uv run python manage.py seed_demo
- uv run pytest -m "not e2e"                              # fast tests
- bash scripts/test_all.sh                                # everything (lint, checks, coverage, e2e)
- uv run python manage.py backup_db
- uv run python manage.py build_registers                 # registers for periods exported before Change 8
- uv run python manage.py sync_payroll                    # repair payroll (records, adjustments, registers)

## Definition of done for each phase
1. `bash scripts/test_all.sh` passes (once it exists; before that: ruff + pytest).
2. The server starts without errors.
3. Summarize what changed, list the new test IDs, and give me exact browser steps to verify.
4. Never delete or flush db.sqlite3 or payroll.sqlite3, or squash/delete migrations, without asking me.
