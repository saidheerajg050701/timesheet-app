# Setup: install and run the app

From nothing to the app running in your browser (about 10 minutes), how to update an existing
copy, and what you additionally need to change the app. Problems:
[troubleshooting](troubleshooting.md).

## What you need

| Item | Minimum | Notes |
|---|---|---|
| Computer | a Mac with macOS 13 or newer (Linux works too) | 8 GB RAM and 5 GB free disk or more |
| Git | any recent version | `git --version`; on a Mac `xcode-select --install` if missing |
| uv | any recent version | `brew install uv` (Mac with Homebrew); Linux: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Internet | for the install | the app itself runs offline |

uv downloads Python 3.13 by itself (the version is in `.python-version`).

## First run

Type each command in **Terminal** and check the ✅ result before going on.

1. **Download the app**
   ```bash
   git clone https://github.com/saidheerajg050701/timesheet-app.git ~/Documents/timesheet-app
   cd ~/Documents/timesheet-app
   ```
   ✅ `ls` shows `manage.py`.

   > **Keep it out of iCloud.** If your Mac syncs *Desktop & Documents Folders* to iCloud
   > (System Settings → your name → iCloud → iCloud Drive), turn that off, or clone to
   > `~/Projects/timesheet-app` instead. iCloud can lock or damage the database files.

2. **Check your computer**
   ```bash
   bash scripts/doctor.sh
   ```
   ✅ It ends with `✅ Ready to RUN the app.` It gives two answers ([D-147](../decisions/D-147-doctor-sh-gives-two-answers.md)): *Ready to RUN* needs only
   Git, uv, Python 3.13 (via uv) and a free port 8000 — anything missing is ❌. *Ready to BUILD
   with Claude Code* only matters if you want to change the app — missing items are ⚠️.

3. **Install the app's software**
   ```bash
   uv sync
   ```
   ✅ It ends with `Installed … packages`.

4. **Create your private settings file**
   ```bash
   cp .env.example .env
   uv run python -c "import secrets; print(secrets.token_urlsafe(50))"
   open -e .env             # opens it in TextEdit; on Linux use any text editor
   ```
   In `.env`, **change these two lines** (the example values are refused,
   [D-145](../decisions/D-145-the-secret-key-can-t-stay-the.md), [D-146](../decisions/D-146-seed-demo-refuses-the-example-demo-password.md)):
   - `DJANGO_SECRET_KEY=` → the long random text the second command printed.
   - `DEMO_PASSWORD=` → a password of your own, 12+ characters. All demo logins use it.

   Leave the other lines as they are (every setting is explained in
   [architecture → Settings](../architecture.md#settings-and-configuration)). Then:
   ```bash
   uv run python manage.py check
   ```
   ✅ `System check identified no issues (1 silenced).` `.env` is private and never committed.

5. **Create the two databases**
   ```bash
   uv run python manage.py migrate
   uv run python manage.py migrate --database=payroll
   ```
   ✅ `Applying … OK` lines and no errors; `db.sqlite3` and `payroll.sqlite3` now exist.
   (`make migrate` runs both.)

6. **Fill in the demo company**
   ```bash
   uv run python manage.py seed_demo
   ```
   ✅ `Demo company created:` followed by counts. What it builds: [demo data](demo-data.md).

7. **Start the app**
   ```bash
   uv run python manage.py runserver        # or: make run
   ```
   ✅ `Starting development server at http://127.0.0.1:8000/`. Open http://127.0.0.1:8000 and
   log in as `dev2@yourcompany.com` with your `DEMO_PASSWORD`: you see Sara's **Dashboard**.
   Stop the app with Control + C.

## First look

Log in as each of these (all use your `DEMO_PASSWORD`); the [user guides](../user-guides/)
explain every page.

| Log in as | What to look at |
|---|---|
| `dev2@yourcompany.com` (employee) | **Timesheets** → this week: the grid, **+ Add row**, click a day, the ⋮ row menu, **Save draft** / **Submit**. **Dashboard**. **Reports → Project hours** ([employee guide](../user-guides/employee.md)) |
| `eng.manager@yourcompany.com` (manager) | **Approvals**, **Change requests**, **Team**, **Reports → Project hours** and **Project budget** ([manager guide](../user-guides/manager.md)) |
| `payroll@yourcompany.com` (payroll) | **Payroll**: registers, **Pending approvals**, **Corrections**; **Reports → Project budget** ([payroll guide](../user-guides/payroll.md)) |
| `hr@yourcompany.com` (HR admin) | **Admin**: employees, pay, teams, projects, tasks, budgets ([HR guide](../user-guides/hr-admin.md)) |
| `ceo@yourcompany.com` (top manager) | **Team**: the whole company |

## Updating an existing copy

```bash
cd ~/Documents/timesheet-app
uv run python manage.py backup_db                    # a backup of both databases first
git pull
uv sync
uv run python manage.py migrate
uv run python manage.py migrate --database=payroll
```
Start the app again and reload the browser page once with ⌘⇧R. What changed in each version:
[CHANGELOG](../../CHANGELOG.md). Notes for older copies:

- `migrate` adds the 9 standard tasks (PLN, DES, DEV, TST, REL, SUP, SEC, DOC, MTG) and allows
  them on every existing project; project work saved before tasks existed shows "Task not
  recorded" and needs a task when its week is saved again (Change 10).
- `migrate` renames older PRJ-xxx project codes to I-xxx (same number) and prints each rename
  (Change 10b).
- Employee pay and project budgets start empty on an existing database (Change 12): HR enters
  them in Admin, or [rebuild the demo data](demo-data.md#start-over-with-fresh-demo-data).
- Refactor R2 adds four bookkeeping migrations that change no table and no row.
- **Only once**, if you exported payroll with a version from before the pay period registers
  (Change 8): `uv run python manage.py build_registers` (safe to repeat; see
  [payroll run](payroll-run.md#registers-for-older-exports)).

## Letting others on your network use it

For a small, trusted office network only (plain HTTP, [D-97](../decisions/D-097-manage-py-check-deploy-https-only-warnings.md)): add your computer's IP address to
`DJANGO_ALLOWED_HOSTS` in `.env`, run `uv run python manage.py runserver 0.0.0.0:8000` and share
`http://<your-ip>:8000`. For company-wide use, move to a server with PostgreSQL and HTTPS
(`config/settings/production.py` is a skeleton for that, not used yet).

## To change the app (developers)

`bash scripts/doctor.sh` should also say `✅ Ready to BUILD with Claude Code`. That needs:

| Tool | Check | Install |
|---|---|---|
| Xcode Command Line Tools (Mac) | `xcode-select -p` | `xcode-select --install` |
| Homebrew (Mac) | `brew --version` | see https://brew.sh |
| Claude Code | `claude --version` | `curl -fsSL https://claude.ai/install.sh \| bash`, then a new Terminal |
| Antigravity (optional editor) | `ls -d /Applications/Antigravity.app` | antigravity.google/download |
| Git name and email | `git config --show-origin user.name` | `git config --global user.name "Your Name"` and `user.email` |
| Chromium for the browser tests | — | `uv run playwright install chromium` (once) |

- Do **not** set an `ANTHROPIC_API_KEY` environment variable: Claude Code would bill that key
  instead of your Claude plan.
- Your home folder must not be a Git repository: `cd ~ && git rev-parse --show-toplevel` should
  say `fatal: not a git repository`.

Then read [CONTRIBUTING](../../CONTRIBUTING.md), [architecture](../architecture.md) and
[testing](../testing.md).
