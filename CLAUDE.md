# Timesheet App — instructions for Claude Code

## Source of truth
- What the app must do: docs/requirements.md. How it is built: docs/architecture.md. Every
  decision: docs/decisions/ (one file per decision, D-01 … D-174, index in README.md). Tests:
  docs/testing.md. Follow them exactly; if something is unclear, ask me before guessing.
- If a decision file conflicts with anything else, the decision wins.
- docs/BUILD_GUIDE.md is the historical build log (phase prompts, Part A/C); its B.x and D.x
  headings only point to the new pages. Don't add new rules there.
- Build only the change I ask for. Stop when that change is done.

## Stack (do not substitute without asking)
Python 3.13 via uv; Django 5.2 LTS; two SQLite databases (default = db.sqlite3, payroll = payroll.sqlite3)
with a database router for the payroll app; django-environ; argon2-cffi (Argon2 password hashing);
django-axes; Faker; Django templates + Bootstrap 5 + HTMX + Chart.js
(vendored in static/vendor, no JS build step); pytest, pytest-django, factory_boy, time-machine,
pytest-cov, Playwright for Python; Ruff. Notifications are OUT of scope for version 1.

## Conventions
- Apps (in apps/): directory, timesheets, projects, compensation, payroll, audit, analytics,
  reports. Settings package: config/settings/.
- Every app uses a services package: <app>/services/<module>.py (e.g. apps/payroll/services/publish.py,
  apps/analytics/services/metrics.py); never a single services.py. Business rules live there as plain,
  tested functions. Views stay thin.
- Every view enforces permissions server-side via apps/directory/services/permissions.py.
- Payroll models live only in the payroll database; no foreign keys across databases; payroll
  records are append-only as defined in D-15 (supersede, never edit). publish_period must be idempotent.
- Pay period registers (D-132–D-138): OPEN/READY are worked out live; only "Finalize & export"
  (apps/payroll/services/register/ → finalize) creates a batch and saves the frozen register and
  lines; all register numbers come from PayrollWeek/PayrollAdjustment records. "Who must be
  approved" is approvals.must_be_approved, nowhere else. A register is READY only when everyone
  is approved (D-142). When an approver may approve / reject / edit is
  approvals.decision_blockers / edit_blockers only (Change 9, D-139–D-141); an edit from
  Approvals never sets submitted_at (that keeps "not submitted by employee" and MISSED).
- Passwords: Argon2 first in PASSWORD_HASHERS; never log, print or store plain passwords.
- Durations are integer minutes; work dates are DateField; deadlines computed in COMPANY_TZ.
- Weeks run Sunday–Saturday and are identified by their Sunday; pay periods start on the Sunday
  PAY_PERIOD_ANCHOR (D-111, D-113). Use apps/timesheets/services/calendar.py, never weekday() arithmetic.
- Weekly grid row actions (change project/category, delete row) only rewrite the week as typed
  through apps/timesheets/services/grid_rows.py and re-draw the grid; nothing is saved until the week is
  saved through save_week / edit_directly, where every entry rule and the audit live (D-129, D-130).
- Use TextChoices for all statuses. Every manager/admin/payroll action writes an AuditLog row
  (system actions use system_actor instead of actor, D-14).
- Project work is booked to a project and a task (D-148–D-152): the task rule lives only in
  apps/timesheets/services/validation.py with apps/projects/services/tasks.py; the charge code
  "<project>-<task>" is computed by tasks.charge_code, never stored. Payroll never sees tasks.
- Project codes are I-001, I-002, … (D-155): assigned only by apps/projects/services/projects.py
  (assign_code, never typed or edited, never reused) and sorted by Project.number, never as text.
  Project search matching lives only in projects.search_projects (D-157).
- Reports → Project hours (D-160–D-164): every number comes from
  apps/reports/services/project_report/ (page, Excel and CSV alike; who is in it only from
  report_people; which People / Group by choices are offered only from scope_options /
  group_options, D-165); report_files.py only lays out files, with safe_cell text, no reasons,
  and one EXPORT audit row per download.
- Pay (D-166, D-167): only through apps/compensation/services/pay.py (rate in force by date, suggested
  salary ÷ 2,080, labour_cost) and pay_import.py; PayRecord is append-only history (a change or
  correction is a new record); Decimal cents, never float; only admins see salaries or pay
  history (can_manage_pay); never log an amount. Costs (D-169–D-171): only from
  apps/reports/services/project_costs.py, APPROVED hours only, rounded per entry; managers see
  their tree, payroll and admins everyone (can_see_costs / can_see_everyones_costs).
- Layout (D-173, D-174): every app is in apps/ and imported as apps.<app>, with its label
  unchanged (directory, timesheets, projects, compensation, payroll, audit, analytics,
  reports). Projects and tasks are apps.projects; pay is apps.compensation (salary permissions
  in apps/compensation/services/access.py); Project hours and Project budget are apps.reports.
  Each app keeps its templates in apps/<app>/templates/<app>/ and its JS in
  apps/<app>/static/<app>/; only site-wide files stay in templates/ and static/. A model moved
  to another app keeps its table (Meta.db_table) and moves with state-only migrations
  (SeparateDatabaseAndState). Settings are config/settings/{base,local,test,production}.py
  (local is the default, pytest uses test, production is a skeleton not used yet). An app with
  several view files has a views/ package (apps/timesheets/views/{weeks,approvals,requests}.py,
  apps/analytics/views/{dashboard,team}.py). A big service may be a package whose
  __init__.py re-exports its public names (apps/directory/services/demo/,
  apps/reports/services/project_report/, apps/payroll/services/register/). Tests live in
  tests/<app>/unit/ and tests/<app>/integration/, whole-site checks in tests/site/, browser tests
  in tests/e2e/test_<area>.py with shared helpers in tests/e2e/helpers.py.
- Tests: follow docs/testing.md (layout, test IDs, factories, fixed clock). Every new rule gets
  tests in the same change. New catalogued tests continue at T-271 and get a row in the
  docs/testing.md table (D-16). Each catalogued test's docstring starts with its ID (D-17).
- Decisions: a new decision takes the next number (D-175 …) as a new file
  docs/decisions/D-NNN-<short-title>.md (same shape as the others) plus a row in
  docs/decisions/README.md; when it changes an earlier decision, say so and link it from the
  earlier file.
- Docs: each change updates the user guides, runbooks, requirements and architecture it affects,
  and adds a CHANGELOG.md entry (and a row in the BUILD_GUIDE Build progress table).
- Never commit .env, db.sqlite3 or payroll.sqlite3. Keep .env.example up to date; if you change
  its DJANGO_SECRET_KEY or DEMO_PASSWORD example values, update apps/directory/checks.py and seed_demo
  (they refuse those values, D-145, D-146; T-225/T-226 check they match).
- Always run Python through uv (`uv run ...`); add packages with `uv add`, never pip.

## Commands
- make help                                                # lists the everyday commands below
- uv run python manage.py runserver                       # http://127.0.0.1:8000 (make run)
- uv run python manage.py migrate && uv run python manage.py migrate --database=payroll
- uv run python manage.py seed_demo
- uv run pytest -m "not e2e"                              # fast tests
- bash scripts/test_all.sh                                # everything (lint, checks, coverage, e2e)
- uv run python manage.py backup_db
- uv run python manage.py build_registers                 # registers for periods exported before Change 8
- uv run python manage.py sync_payroll                    # repair payroll (records, adjustments, registers)

## Definition of done for each change
1. `bash scripts/test_all.sh` passes (once it exists; before that: ruff + pytest).
2. The server starts without errors.
3. Summarize what changed, list the new test IDs, and give me exact browser steps to verify.
4. Never delete or flush db.sqlite3 or payroll.sqlite3, or squash/delete migrations, without asking me.
