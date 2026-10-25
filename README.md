# Employee Timesheet App

A local-only Django web app for weekly timesheets, biweekly approvals and a separate payroll
database. The full specification is [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md).

## Setup on a new Mac
1. Install the tools from the guide's Part A (Homebrew, uv, Git) and check them:
   ```bash
   bash scripts/doctor.sh                     # until it says "Ready to build"
   ```
2. Get the code into `~/Documents/timesheet-app` (keep it out of iCloud-synced folders, see D.2) and install the packages:
   ```bash
   cd ~/Documents/timesheet-app
   uv python install 3.13                     # if doctor.sh says Python 3.13 is missing
   uv sync                                    # Python packages into .venv
   uv run playwright install chromium         # browser for the end-to-end tests (once)
   ```
3. Create your private settings file (never commit it):
   ```bash
   cp .env.example .env
   uv run python -c "import secrets; print(secrets.token_urlsafe(50))"   # paste as DJANGO_SECRET_KEY
   ```
   Then edit `.env`: the secret key, `DEMO_PASSWORD` (12+ characters), `COMPANY_EMAIL_DOMAIN`,
   `COMPANY_TZ`, and keep `DJANGO_DEBUG=False` for daily use (error pages then never show code
   or settings).
4. Create both databases and, if you want, the demo company:
   ```bash
   uv run python manage.py migrate                      # main database  → db.sqlite3
   uv run python manage.py migrate --database=payroll   # payroll database → payroll.sqlite3
   uv run python manage.py seed_demo                    # optional demo data (refuses if data exists)
   ```

After pulling new code later, run `uv sync` and both `migrate` commands again.

## Run
```bash
uv run python manage.py runserver          # http://127.0.0.1:8000 — stop with Control + C
```

## Demo logins
After `seed_demo`, these accounts exist; all use the `DEMO_PASSWORD` you put in `.env`.

| Email | What to try |
|---|---|
| `hr@yourcompany.com` | Admin: Django Admin, everyone's team view |
| `ceo@yourcompany.com` | Admin and top-level manager |
| `eng.director@yourcompany.com` | Manager of managers (Team shows indirect reports) |
| `eng.manager@yourcompany.com` | Manager: approvals and change requests |
| `dev1@yourcompany.com`, `dev2@yourcompany.com` | Employees |
| `ops.manager@yourcompany.com` | Manager of a second team |
| `payroll@yourcompany.com` | Payroll only |
| `finance.manager@yourcompany.com` | Payroll and manager |

`qa1@`, `ops1@` and `ops2@yourcompany.com` have no account yet: use them to try **Sign up**.

## Logging in
Every page needs a login except `/login/` and `/signup/`. Sign-up only works for an ACTIVE
employee in the directory, using their company email. Five wrong passwords lock that account
for 15 minutes. There is no self-service password reset: ask an admin.

## Roles and menus
Everyone gets Dashboard, Timesheets, Requests and Profile. Team and Approvals appear for
managers (anyone with reports) and directory admins; Payroll for payroll users and admins;
Admin only for directory admins. Every page also checks permissions on the server
(`directory/services/permissions.py`).

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

## Admin (HR)

Directory admins open **Admin** (`/admin/`); everyone else gets 403. Every change is written to the audit log with the admin's name.

- **Employees, teams, projects:** add and edit. Nothing can be deleted: deactivate employees and clear *Active* on projects instead.
- **Deactivate / Reactivate:** select employees in the list and choose the action. Deactivate asks for the end date (today by default) and logs the person out; their history stays and their submitted weeks can still be approved and paid.
- **Reset password:** on an employee's page. HR types a temporary password; the person must choose a new one at their next login. Any login lockout is cleared.
- **Import CSV / Export CSV:** on the employee list. Export uses the same columns as import, so you can edit the file and import it again; you always see a summary (or the errors with line numbers) before anything changes.
- Timesheets, approvals, change requests, payroll records and the audit log are read-only here.

## Look and feel
One theme stylesheet, `static/css/theme.css`, styles every page on top of the vendored Bootstrap:
colours, spacing, corners and shadows are CSS variables (`--ts-*`) at its top, so a brand
colour change happens in one place. Fonts are the system fonts (nothing is downloaded). Week,
period, request and payroll statuses always use the same badge component
(`templates/includes/status_badge.html`).

To review the pages yourself, take screenshots of the main pages for an employee, a manager,
payroll and HR at laptop and phone width (uses the test databases only, never your data):
```bash
SCREENSHOTS_DIR=~/Desktop/timesheet-screenshots uv run pytest scripts/visual_review --browser-channel chrome
```

## Demo data and the employee directory
```bash
uv run python manage.py seed_demo            # demo company: ~50 employees, 12–13 weeks of history
uv run python manage.py seed_demo --large    # ~500 employees, 52 weeks (performance testing)
uv run python manage.py import_employees data/your_file.csv   # create/update employees by employee_code
```
`seed_demo` refuses to run when the database already has data. Every demo login uses the
`DEMO_PASSWORD` from `.env`.

To create an admin login for an existing directory admin employee (ACTIVE, `is_admin` on,
no account yet):
```bash
uv run python manage.py createsuperuser    # asks for the employee code, e.g. EMP-0007
```

## Test
```bash
uv run pytest -m "not e2e"                 # fast unit + integration tests (~1 minute)
uv run pytest -m e2e                       # end-to-end tests in a real browser (needs Chromium, see setup)
bash scripts/test_all.sh                   # everything: ruff, migrations, Django check, coverage ≥ 80 %, e2e
uv run pytest -m "not e2e" --cov --cov-report=html   # coverage report → open htmlcov/index.html
```
Tests use their own temporary databases and a fixed clock; they never touch `db.sqlite3` or
`payroll.sqlite3`. The end-to-end tests start a test server by themselves. No Chromium yet? Use
your installed Google Chrome: `bash scripts/test_all.sh --browser-channel chrome`.

## Backup and restore
Back up **both** databases at once (safe while the app runs):
```bash
uv run python manage.py backup_db          # → backups/db-<stamp>.sqlite3 and backups/payroll-<stamp>.sqlite3
```
Copy the `backups/` folder somewhere safe (it is not in Git). To restore:
1. Stop the server (Control + C).
2. Pick **one** timestamp and copy both files back — always both from the same time:
   ```bash
   cp backups/db-20261024-120953.sqlite3 db.sqlite3
   cp backups/payroll-20261024-120953.sqlite3 payroll.sqlite3
   ```
   (Keep the files you replace, e.g. rename them to `*-old.sqlite3` first, until you have checked the result.)
3. Start the server, then repair anything approved after that backup:
   ```bash
   uv run python manage.py sync_payroll
   ```

## Known limitations (version 1)
- Runs on one Mac with SQLite over plain HTTP: fine for one person or a trusted office network, not for the internet (no HTTPS; see B.12 D-97).
- No notifications or email, so no "forgot password" link: HR sets a temporary password in Admin.
- No holiday calendar (enter Holiday rows by hand) and no delegated approvals when a manager is away.
- All deadlines use one company time zone (`COMPANY_TZ`).
- The payroll CSV is the app's own format, not a payroll provider's.
- Changing someone's expected weekly hours applies to every week shown afterwards (no history per week).

## Layout
- `config/`: settings (read from `.env`), URLs
- `directory/`, `timesheets/`, `audit/`, `payroll/`, `analytics/`: Django apps. Business rules live in each app's `services/` package
- `payroll/routers.py`: sends the payroll app to `payroll.sqlite3` and keeps every other app out of it
- `templates/`, `static/vendor/`: Bootstrap 5, HTMX and Chart.js, saved locally (no JS build step)
- `tests/`: pytest suite (see B.11 in the guide); `scripts/visual_review/`: the screenshot tool
