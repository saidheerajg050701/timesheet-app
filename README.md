# Employee Timesheet App

A web app that runs on your own computer for weekly timesheets, two-week approvals and a separate
payroll database. Employees enter their hours in a weekly grid, managers approve every
two weeks, and payroll exports one register per pay period. The full specification is
[docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md).

## Quick start (about 10 minutes)

Type each command in **Terminal** (Applications → Utilities → Terminal). After each step,
check that you see the ✅ result before going on.

**1. What you need:** a Mac with macOS 13 or newer (Linux works too), **Git** and **uv**.
```bash
git --version
```
✅ You see something like `git version 2.4x`. If not, on a Mac run `xcode-select --install`.
```bash
brew install uv          # Mac with Homebrew; on Linux: curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```
✅ You see `uv 0.x.x`.

**2. Download the app**
```bash
git clone https://github.com/saidheerajg050701/timesheet-app.git ~/Documents/timesheet-app
cd ~/Documents/timesheet-app
```
✅ `Cloning into '…/timesheet-app'… done.` and `ls` shows `manage.py`.

> **Keep it out of iCloud.** If your Mac syncs *Desktop & Documents Folders* to iCloud
> (System Settings → your name → iCloud → iCloud Drive), turn that off, or clone to
> `~/Projects/timesheet-app` instead. iCloud can lock or damage the database files.

**3. Check your computer**
```bash
bash scripts/doctor.sh
```
✅ It ends with `✅ Ready to RUN the app.` (The second line, about *building with Claude Code*,
only matters if you want to change the app; ⚠️ there is fine.)

**4. Install the app's software**
```bash
uv sync
```
✅ It ends with `Installed … packages`. uv downloads Python 3.13 by itself if needed (the
version is in `.python-version`).

**5. Create your private settings file**
```bash
cp .env.example .env
uv run python -c "import secrets; print(secrets.token_urlsafe(50))"
open -e .env             # opens it in TextEdit; on Linux use any text editor
```
In `.env`, **you must change these two lines** (the example values are refused):
- `DJANGO_SECRET_KEY=` → paste the long random text the second command printed.
- `DEMO_PASSWORD=` → a password of your own, 12+ characters. All demo logins will use it.

Leave the other lines as they are for now. Save the file, then check:
```bash
uv run python manage.py check
```
✅ `System check identified no issues (1 silenced).` If it says the secret key is still the
example, go back to step 5. `.env` is private: it is never uploaded to Git.

**6. Create the two databases**
```bash
uv run python manage.py migrate
uv run python manage.py migrate --database=payroll
```
✅ Each one lists `Applying … OK` lines and ends without errors. You now have `db.sqlite3` and
`payroll.sqlite3` in the folder.

**7. Fill in the demo company**
```bash
uv run python manage.py seed_demo
```
✅ `Demo company created:` followed by counts (employees, accounts, timesheets, payroll …).

**8. Start the app**
```bash
uv run python manage.py runserver
```
✅ `Starting development server at http://127.0.0.1:8000/`. Open **http://127.0.0.1:8000** in
your browser and log in as **`dev2@yourcompany.com`** with your `DEMO_PASSWORD`.
✅ You see Sara's **Dashboard**. To stop the app, press Control + C in Terminal.

### First look
Log out (top right) and in again as each of these. They all use your `DEMO_PASSWORD`:

| Log in as | What to look at |
|---|---|
| `dev2@yourcompany.com` (employee) | **Timesheets** → this week: the weekly grid. **+ Add row** (Project work asks for a project, then one of its tasks), click a day to enter times, the ⋮ menu on a row, **Save draft** / **Submit**. **Dashboard**: hours by task and by charge code. **Reports → Project hours**: your own hours; download Excel or CSV. |
| `eng.manager@yourcompany.com` (manager) | **Approvals**: the last finished pay period. Open a person: approve, reject, or for a **Locked** (never submitted) person **Edit** their week and then approve it. **Change requests**, **Team**. **Reports → Project hours** with Group by **Manager**. |
| `payroll@yourcompany.com` (payroll) | **Payroll**: one register per pay period (Open → Ready → Finalize & export → Paid), **Pending approvals** (who still has to approve) and **Corrections**. |
| `hr@yourcompany.com` (HR admin) | **Admin**: employees, teams, projects (with their **Allowed tasks**), **Tasks**, deactivate, reset passwords, CSV import/export; **Pending approvals** in the Admin header. **Reports → Project hours**: everyone. Also try `eng.director@yourcompany.com` (director): all their managers' groups. |
| `ceo@yourcompany.com` (top manager) | **Team**: the whole company. |

## Updating an existing copy
When there is a new version:
```bash
cd ~/Documents/timesheet-app
uv run python manage.py backup_db                    # a backup of both databases first
git pull
uv sync
uv run python manage.py migrate
uv run python manage.py migrate --database=payroll
```
Then start the app again (`runserver`) and reload the browser page once with ⌘⇧R (Command +
Shift + R).

`migrate` also adds the 9 standard tasks (PLN, DES, DEV, TST, REL, SUP, SEC, DOC, MTG) and
allows all of them on every existing project. Project work saved before tasks existed keeps no
task and shows **"Task not recorded"**; a week like that needs a task on its project rows when
it is saved again.

Project codes are **I-001, I-002, …** since Change 10b. `migrate` renames older PRJ-xxx codes
to I-xxx (same number) and prints each rename; old audit rows keep the old code. While you only
have demo data, it is simplest to start again with fresh demo data instead:
```bash
uv run python manage.py backup_db                    # a backup first
mkdir -p backups/before-10b && mv db.sqlite3 payroll.sqlite3 backups/before-10b/
uv run python manage.py migrate
uv run python manage.py migrate --database=payroll
uv run python manage.py seed_demo
```

**Only once**, if you used a version from before the pay period registers (Change 8) and had
already exported payroll, also run this (it is safe to repeat):
```bash
uv run python manage.py build_registers              # registers for periods you already exported
```

## Troubleshooting
- **"That port is already in use" / port 8000 busy.** Another copy is still running: stop it
  with Control + C in its Terminal window. Or use another port:
  `uv run python manage.py runserver 8001` and open http://127.0.0.1:8001.
- **`seed_demo` says the database already has data.** It never overwrites anything. To start
  over with a fresh demo, **move** the databases away (never delete them):
  ```bash
  mkdir -p backups/old && mv db.sqlite3 payroll.sqlite3 backups/old/
  uv run python manage.py migrate && uv run python manage.py migrate --database=payroll
  uv run python manage.py seed_demo
  ```
- **"DJANGO_SECRET_KEY is still the example value" or "…is only N characters".** Make a new
  key with `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` and paste it
  into `.env` as `DJANGO_SECRET_KEY`. With `DJANGO_DEBUG=False` the app won't start until you do.
- **"DEMO_PASSWORD is still the example value".** Put a password of your own (12+ characters)
  in `.env` as `DEMO_PASSWORD`, then run `seed_demo` again.
- **"Account locked" after wrong passwords.** Wait 15 minutes, or ask HR to reset the password
  (Admin → the employee → Reset password).
- **Forgot the demo password.** It is the `DEMO_PASSWORD` line in your `.env` file.
- **Payroll says "out of sync".** Run `uv run python manage.py sync_payroll` (safe to repeat).
- **Browser tests can't find Chromium.** Run `uv run playwright install chromium` once, or use
  your Google Chrome: `bash scripts/test_all.sh --browser-channel chrome`.
- **A page looks wrong right after an update.** Reload it once with ⌘⇧R.

## Demo logins
After `seed_demo`, these accounts exist. All use the `DEMO_PASSWORD` you put in `.env`.

| Email | Who | What to try |
|---|---|---|
| `hr@yourcompany.com` | Lena Ortiz | Admin: Django Admin, everyone's team view, approves the CEO |
| `ceo@yourcompany.com` | Asha Rao | Admin and top-level manager |
| `eng.director@yourcompany.com` | Mark Lee | Manager of managers (Team shows indirect reports) |
| `eng.manager@yourcompany.com` | Priya Shah | Manager: approvals and change requests |
| `dev1@yourcompany.com`, `dev2@yourcompany.com` | John Kim, Sara Ng | Employees |
| `ops.manager@yourcompany.com` | Tom Hall | Manager of a second team |
| `payroll@yourcompany.com` | Nina Patel | Payroll only |
| `finance.manager@yourcompany.com` | Omar Diaz | Payroll and manager |

`qa1@`, `ops1@` and `ops2@yourcompany.com` have no account yet: use them to try **Sign up**.

## Logging in
Every page needs a login except `/login/` and `/signup/`. Sign-up only works for an ACTIVE
employee in the directory, using their company email. Five wrong passwords lock that account
for 15 minutes. There is no self-service password reset: ask an admin.

## Roles and menus
Everyone gets Dashboard, Timesheets, Requests, Reports and Profile. Team and Approvals appear for
managers (anyone with reports) and directory admins; Payroll for payroll users and admins;
Admin only for directory admins. Every page also checks permissions on the server
(`directory/services/permissions.py`).

## Dashboard
The home page shows your own last 4, 12 or 26 weeks: this week's status with a live countdown
to Saturday 12:00, hours worked per week against expected hours, on-time / late / missed
weeks, overtime (same rule as payroll), hours by project and by category (Break shown
separately, unpaid), **hours by task** and **hours by project + task** (by charge code, e.g.
I-001-DEV; older project work without a task is its own "Task not recorded" line), and the
approval outcome of each pay period. Every chart also lists its
numbers. A week you never submitted counts as missed, even if your manager approved it later.

## Team
Managers open **Team** (`/team/`) to see the people under them; admins see everyone. Filters: whole tree or direct reports, team, last 4 / 12 / 26 weeks.
The page shows team hours per week against expected, average utilization (hours worked ÷ (expected − leave), finished weeks), a sortable table per person,
who hasn't submitted this week, hours by project, by task and by project + task (charge code). Click a name for a read-only view of that person's dashboard and timesheets.

Measure how fast the page is for someone (read-only, prints seconds and query count):

```bash
uv run python manage.py time_team_page ceo@yourcompany.com
uv run python manage.py time_team_page ceo@yourcompany.com --weeks 26 --direct
```

## Reports — Project hours
Everyone has **Reports** in the menu (`/reports/project-hours/`).
- **Who sees what:** employees (payroll staff too) see only their own hours. Managers see
  themselves and everyone below them; directors therefore see all their managers' groups;
  HR admins see everyone. Asking for anyone else's hours gives "Not allowed" (403).
- **Filters** (they stay in the address, so you can share the link): **Period** (this or last
  pay period, last 4 or 12 weeks, or your own dates — always whole Sunday–Saturday weeks, at
  most 53), **Projects** (type an I-code or name and pick one or more; none = all projects),
  **Hours** (Approved, Approved + Submitted, or Everything entered). Managers also choose
  **People** (whole tree, direct reports only, or one manager's group), **Group by** (team or
  manager) and **Show people with no hours**.
- **What it shows:** project hours, non-project time (Meetings, Training, Other — never
  filtered by project) and total time; by project (with a chart), by task (including "Task
  not recorded"), project × task and by week. Managers also get by team or **by manager**
  ("own group" adds up to the total, "including everyone below" is the roll-up; click a
  manager to look at their group) and **by employee**: everyone in scope, with 0.00 rows and
  a note such as "Hours not approved yet" or "On leave". Break and leave are never counted.
- **Downloads:** **Excel** (one tab per section) and **CSV** (one row per entry, never the
  reason), named like `project-hours_2026-09-27_to_2026-10-10.xlsx`. Each download is written to
  the audit log. A whole year for ~500 people takes about half a minute as Excel; the CSV is
  quicker for that much.
- How long it takes for someone (read-only):
  ```bash
  uv run python manage.py time_project_report hr@yourcompany.com --period 12w
  ```

## Timesheets
`/timesheets/` lists your recent weeks. A week is a **grid**: one row per category, or per
project **and task** for Project work, a column per day (a week runs **Sunday to Saturday**) and a
**Total worked hours** column and footer.
- **Tasks and charge codes:** Project work is always booked to a project **and** one of that
  project's tasks (for example DEV Development or TST Testing & QA). The row shows
  "I-001 Customer Portal · DEV Development" and its **charge code** I-001-DEV. Other
  categories (Meetings, Training, Break, leave …) have no project and no task. Older project
  work saved before tasks existed shows **"Task not recorded"**; when such a week is saved
  again, choose a task for that row (the ⋮ menu does it for the whole row).
- **+ Add row** adds a category; Project work also asks for the project and then one of its
  active tasks. Each category, or project + task, has one row, so using **+ Add row** again for
  one that is already there takes you to its row.
- **Finding a project:** the Project box is a search. Type part of an I-code or a name
  ("i-002", "001", "portal" — any case), then click the project or use ↑/↓ and Enter; Esc
  closes the list. With nothing typed it shows **Your recent projects** (the ones used in the 4
  weeks before this week) and then all active projects, sorted by I-code. "No matching project"
  means nothing fits; inactive projects never appear.
- **Click a day to enter time.** Work and Break use one or more time slots with a start and an
  end (15-minute steps, same day, no overlaps) and an optional reason. Leave (PTO, Sick, Holiday)
  uses hours and an optional reason.
- **Twice in a day:** to work on the same project twice (for example 08:00–13:00 and 14:00–17:00
  around a Break), click the day again. Its slots are listed with an empty new one ready to
  fill, or use **+ Add another time slot**. The cell then shows e.g. "8.00 · 2 slots", and its
  tooltip lists the times.
- **Picked the wrong project, task or category?** Each row's **⋮** menu has **Change row**
  (choose another category, project or task; all its slots move; dates, times and reasons stay;
  if the new one already has a row they merge) or **Delete row** (after a confirmation showing how many slots and hours).
  Both apply to the grid at once and are kept when you save the week.
- **Totals:** Break is unpaid and never counted in Total worked hours; leave is shown
  separately. The day summary below the grid shows first start, last end, hours worked,
  expected hours, Break and Leave. Read-only weeks show a reason only when one was entered.
- **Deadline:** **Save draft** or **Submit** before Saturday 12:00 company time. After that an
  unsubmitted week is locked and counted as missed.
- All rules are checked on the server when you save, and problems are shown on the cell they
  belong to.

## Change requests
On a submitted, locked or approved week, **Request change** sends a reason to your manager
(admins handle employees with no manager; nobody handles their own). `/requests/` shows your
requests. Managers work through **Change requests** (`/approvals/requests/`):
- **Reject**
- **Unlock**: the employee can edit until the later of 48 hours from now and the week's
  Saturday 12:00.
- **Edit directly**: same rules as the timesheet page.

Every step is in the audit log, and changing an approved week puts its pay period back to
pending.

## Approvals
Managers (and admins, for employees with no manager) open **Approvals** to pick a pay period:
14 days, two Sunday-to-Saturday weeks counted from `PAY_PERIOD_ANCHOR`, a Sunday. The default is
the most recent completed one. They review each direct report's two weeks: hours worked (Break
never counts), leave, and Late / Overtime / Missing days flags.
- A period can be **approved** or **rejected** (with a comment) once its weeks are submitted
  **or locked**.
- **Locked weeks** (the employee never submitted): the manager can **Edit** the week in the
  weekly grid, then approve it with the hours entered (after a confirmation) or reject it.
  The week is marked "Not submitted by employee" and still counts as missed. A locked week also
  still has an Unlock button.
- **Reopened weeks** wait for the employee until their window ends.
- **Bulk approve:** clean rows can be approved together.
- Nobody approves their own timesheet.
- **Deadline:** approve each period by **Monday 12:00** after it ends (settings
  `APPROVAL_DEADLINE_DAYS` and `APPROVAL_DEADLINE_TIME`). After that, rows not yet approved are
  marked **Overdue**. Payroll can pay the period only once everyone is approved.

## Payroll
Approved weeks are copied into a separate database, `payroll.sqlite3`, right after the
approval is saved: regular hours up to the expected hours, overtime above, PTO / Sick /
Holiday separately (Break is unpaid and never counted).

**Payroll** (`/payroll/`, payroll staff and admins only) lists every ended pay period, newest
first, with its **register**: one line per employee with Week 1, Week 2 and Period hours, the
**carry-forward** columns (highlighted) and the **Pay total**, plus a totals row.
- **Open**: approvals are still coming in. You see how many are approved and who is still
  pending (no hours yet). **Pending approvals** lists, per manager, who still has to be
  approved and why (also as CSV). HR finds it in the Admin header too.
- **Ready**: every person who must be approved is approved (locked weeks included) and no change
  request is open. The deadline alone never makes a period ready.
- **Finalize & export** saves the register for good as one batch (`EXP-0007`). Download the
  **Register CSV** and the **Detailed CSV** (week and adjustment rows) as often as you like;
  **Download all periods** gives every finalized register in one file. Then **Mark as paid**.

Records are append-only: a changed week is superseded, and a new version is written after
re-approval. If the week was already in a finalized register, the difference (for example
+2.00 overtime hours or −1.50 regular hours) becomes a **pay adjustment**. It goes in the
carry-forward columns of the next register that isn't finalized yet. Someone approved after
their register was finalized is carried forward the same way. **Corrections** lists every
changed week and the register that pays its difference. If the page says payroll is out of
sync, run:
```bash
uv run python manage.py sync_payroll       # safe to repeat; also creates missing adjustments and registers
```

## Admin (HR)

Directory admins open **Admin** (`/admin/`); everyone else gets 403. Every change is written to the audit log with the admin's name.

- **Employees, teams, projects:** add and edit. Nothing can be deleted: deactivate employees and clear *Active* on projects instead.
- **Project codes** are assigned by the app: a new project gets the next I-code (I-001, I-002, …, I-1000 after I-999) when you save. You only type the name; the code is shown after saving and can never be edited or reused.
- **Tasks** (what project work is spent on: code, name, description, active, sort order): add and edit; the code can't change once added. Clear *Active* instead of deleting. The page shows how many saved entries use the task.
- **Allowed tasks** on a project: tick the tasks people may book to it (a new project starts with every active task ticked). Removing a task, or deactivating one, that saved entries use is allowed: those entries keep it, you get a note saying how many, and open weeks must choose another task when they are saved again.
- **Deactivate / Reactivate:** select employees in the list and choose the action. Deactivate asks for the end date (today by default) and logs the person out; their history stays and their submitted weeks can still be approved and paid.
- **Reset password:** on an employee's page. HR types a temporary password; the person must choose a new one at their next login. Any login lockout is cleared.
- **Import CSV / Export CSV:** on the employee list. Export uses the same columns as import, so you can edit the file and import it again; you always see a summary (or the errors with line numbers) before anything changes.
- **Pending approvals** (in the Admin header): which managers still have people to approve in a pay period. Read only.
- Timesheets, approvals, change requests, payroll records and the audit log are read-only here.

## Look and feel
One theme stylesheet, `static/css/theme.css`, styles every page on top of the vendored Bootstrap:
colours, spacing, corners and shadows are CSS variables (`--ts-*`) at its top, so a brand
colour change happens in one place. Fonts are the system fonts (nothing is downloaded). Week,
period, request and payroll statuses always use the same badge component
(`templates/includes/status_badge.html`).

## Demo data and the employee directory
```bash
uv run python manage.py seed_demo            # demo company: ~50 employees, 12–13 weeks of history
uv run python manage.py seed_demo --large    # ~500 employees, 52 weeks (performance testing)
uv run python manage.py import_employees data/your_file.csv   # create/update employees by employee_code
```
`seed_demo` refuses to run when the database already has data, and it refuses the example
`DEMO_PASSWORD`. Every demo login uses the `DEMO_PASSWORD` from `.env`.

To create an admin login for an existing directory admin employee (ACTIVE, `is_admin` on,
no account yet):
```bash
uv run python manage.py createsuperuser    # asks for the employee code, e.g. EMP-0007
```

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
- Runs on one computer with SQLite over plain HTTP. That's fine for one person or a trusted office network, but not for the internet (no HTTPS; see B.12 D-97).
- No notifications or email, so no "forgot password" link: HR sets a temporary password in Admin.
- No holiday calendar (enter Holiday rows by hand) and no delegated approvals when a manager is away.
- All deadlines use one company time zone (`COMPANY_TZ`).
- The payroll CSV is the app's own format, not a payroll provider's.
- Changing someone's expected weekly hours applies to every week shown afterwards (no history per week).

## For developers / running the tests

**Extra tools.** `bash scripts/doctor.sh` should also say `✅ Ready to BUILD with Claude Code`.
That needs Claude Code, Antigravity, your Git name and email, and the Xcode Command Line Tools.
The browser tests need Chromium once:
```bash
uv run playwright install chromium
```

**Tests**
```bash
uv run pytest -m "not e2e"                 # fast unit + integration tests (~1 minute)
uv run pytest -m e2e                       # end-to-end tests in a real browser
bash scripts/test_all.sh                   # everything: ruff, migrations, Django check, coverage ≥ 80 %, e2e
bash scripts/test_all.sh --browser-channel chrome   # the same, using your installed Google Chrome
uv run pytest -m "not e2e" --cov --cov-report=html  # coverage report → open htmlcov/index.html
```
Tests use their own temporary databases and a fixed clock; they never touch `db.sqlite3` or
`payroll.sqlite3`. The end-to-end tests start a test server by themselves.

**Screenshots for a visual review.** This takes the main pages for an employee, a manager,
payroll and HR at laptop and phone width. It uses the test databases only, never your data:
```bash
SCREENSHOTS_DIR=~/Desktop/timesheet-screenshots uv run pytest scripts/visual_review --browser-channel chrome
```

**Working with Claude Code**
- The rules live in [CLAUDE.md](CLAUDE.md) and the specification in
  [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md): Part B is the source of truth, and B.12 records
  every decision (D-numbers). B.11 lists every test (T-numbers).
- Ask for one change at a time. Claude Code plans first, records new decisions and tests in
  the guide, and runs `bash scripts/test_all.sh` until it passes.
- You review what changed and commit it yourself. `.env`, `db.sqlite3` and `payroll.sqlite3`
  are never committed.

**Layout**
- `config/`: settings (read from `.env`), URLs
- `directory/`, `timesheets/`, `audit/`, `payroll/`, `analytics/`: Django apps. Business rules live in each app's `services/` package
- `payroll/routers.py`: sends the payroll app to `payroll.sqlite3` and keeps every other app out of it
- `templates/`, `static/vendor/`: Bootstrap 5, HTMX and Chart.js, saved locally (no JS build step)
- `tests/`: pytest suite (see B.11 in the guide); `scripts/visual_review/`: the screenshot tool; `scripts/doctor.sh`: the environment check
