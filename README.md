# Employee Timesheet App

A local-only Django web app for weekly timesheets, biweekly approvals and a separate payroll
database. The full specification is [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md).

## Requirements
macOS with the tools from the guide's Part A. Check them with `bash scripts/doctor.sh`.

## First-time setup
```bash
uv sync                                    # installs Python 3.13 packages into .venv
cp .env.example .env                       # then edit .env (never commit it)
uv run python -c "import secrets; print(secrets.token_urlsafe(50))"   # paste as DJANGO_SECRET_KEY
uv run python manage.py migrate                      # main database  → db.sqlite3
uv run python manage.py migrate --database=payroll   # payroll database → payroll.sqlite3
```

## Run
```bash
uv run python manage.py runserver          # http://127.0.0.1:8000
```

## Logging in
Every page needs a login except `/login/` and `/signup/`. Sign-up only works for an ACTIVE
employee in the directory, using their company email. Five wrong passwords lock that account
for 15 minutes. There is no self-service password reset: ask an admin.

## Roles and menus
Everyone gets Dashboard, Timesheets, Requests and Profile. Team and Approvals appear for
managers (anyone with reports) and directory admins; Payroll for payroll users and admins;
Admin only for directory admins. Every page also checks permissions on the server
(`directory/services/permissions.py`). Pages from later build phases show a placeholder.

## Dashboard
The home page shows your own last 4, 12 or 26 weeks: this week's status with a live countdown
to Saturday 12:00, hours worked per week against expected hours, on-time / late / missed
weeks, overtime (same rule as payroll), hours by project and by category (Break shown
separately, unpaid), and the approval outcome of each pay period. Every chart also lists its
numbers.

## Team

Managers open **Team** (`/team/`) to see the people under them; admins see everyone. Filters: whole tree or direct reports, team, last 4 / 12 / 26 weeks.
The page shows team hours per week against expected, average utilization (hours worked ÷ (expected − leave), finished weeks), a sortable table per person,
who hasn't submitted this week, and hours by project. Click a name for a read-only view of that person's dashboard and timesheets.

Measure how fast the page is for someone (read-only, prints seconds and query count):

```bash
uv run python manage.py time_team_page ceo@yourcompany.com
uv run python manage.py time_team_page ceo@yourcompany.com --weeks 26 --direct
```

## Timesheets
`/timesheets/` lists your recent weeks; open one and add as many rows as you need. Each row has
a day, category, project (Project work only) and a reason. Work and Break rows use start and end
times (15-minute steps, same day, no overlaps); leave (PTO, Sick, Holiday) uses hours. Break time
is unpaid and not counted in Hours worked. The day summary shows Hours worked, Break, Leave,
expected hours and each day's first start and last end. **Save draft** or **Submit** before
Saturday 12:00 company time; after that an unsubmitted week is locked and counted as missed.
All rules are checked on the server when you save.

## Change requests
On a submitted, locked or approved week, **Request change** sends a reason to your manager
(admins handle employees with no manager; nobody handles their own). `/requests/` shows your
requests. Managers work through **Change requests** (`/approvals/requests/`): **Reject**,
**Unlock** (the employee can edit until the later of 48 hours from now and the week's Saturday
12:00) or **Edit directly** (same rules as the timesheet page). Every step is in the audit log;
changing an approved week puts its pay period back to pending.

## Approvals
Managers (and admins, for employees with no manager) open **Approvals** to pick a pay period
(14 days, default: the most recent completed one) and review each direct report's two weeks:
hours worked (Break never counts), leave, and Late / Overtime / Missing days flags. A period
can be approved or rejected (with a comment) once its weeks are submitted; a locked week has an
Unlock button. Clean rows can be bulk approved. Nobody approves their own timesheet.

## Payroll
Approved weeks are copied into a separate database, `payroll.sqlite3`, right after the
approval is saved: regular hours up to the expected hours, overtime above, PTO / Sick /
Holiday separately (Break is unpaid and never counted). Payroll staff and admins use
**Payroll** (`/payroll/`) to filter, see totals per employee, **Export CSV** (one numbered
batch per period, safe to open in Excel/Numbers) and **Mark as paid**; **Corrections** lists
weeks that changed after export. Records are append-only: a changed week is superseded and a
new version is written after re-approval. If the page says payroll is out of sync, run:
```bash
uv run python manage.py sync_payroll       # safe to repeat
```
Back up both databases (safe while the app runs): `uv run python manage.py backup_db`.

## Admin (HR)

Directory admins open **Admin** (`/admin/`); everyone else gets 403. Every change is written to the audit log with the admin's name.

- **Employees, teams, projects:** add and edit. Nothing can be deleted: deactivate employees and clear *Active* on projects instead.
- **Deactivate / Reactivate:** select employees in the list and choose the action. Deactivate asks for the end date (today by default) and logs the person out; their history stays and their submitted weeks can still be approved and paid.
- **Reset password:** on an employee's page. HR types a temporary password; the person must choose a new one at their next login. Any login lockout is cleared.
- **Import CSV / Export CSV:** on the employee list. Export uses the same columns as import, so you can edit the file and import it again; you always see a summary (or the errors with line numbers) before anything changes.
- Timesheets, approvals, change requests, payroll records and the audit log are read-only here.

After updating to Phase 11, apply the new migration (main database only):

```bash
uv run python manage.py migrate
```

## Demo data and the employee directory
```bash
uv run python manage.py seed_demo            # demo company: ~50 employees, 12–13 weeks of history
uv run python manage.py seed_demo --large    # ~500 employees, 52 weeks (performance testing)
uv run python manage.py import_employees data/your_file.csv   # create/update employees by employee_code
```
`seed_demo` refuses to run when the database already has data. Every demo login uses the
`DEMO_PASSWORD` from `.env`. The admin at http://127.0.0.1:8000/admin/ is view-only for now.

To create an admin login for an existing directory admin employee (ACTIVE, `is_admin` on,
no account yet):
```bash
uv run python manage.py createsuperuser    # asks for the employee code, e.g. EMP-0007
```

## Test
```bash
uv run pytest -m "not e2e"                 # fast unit + integration tests
bash scripts/test_all.sh                   # ruff, migrations check, Django check, coverage, e2e
```
Tests use temporary databases and never touch `db.sqlite3` or `payroll.sqlite3`.

## Layout
- `config/`: settings (read from `.env`), URLs
- `directory/`, `timesheets/`, `audit/`, `payroll/`, `analytics/`: Django apps. Business rules live in each app's `services/` package
- `payroll/routers.py`: sends the payroll app to `payroll.sqlite3` and keeps every other app out of it
- `templates/`, `static/vendor/`: Bootstrap 5, HTMX and Chart.js, saved locally (no JS build step)
- `tests/`: pytest suite (see B.11 in the guide)
