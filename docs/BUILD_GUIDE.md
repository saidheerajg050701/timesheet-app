# Employee Timesheet Web App — Local Build Guide
## Python + Django · macOS · Google Antigravity · Claude Code

> **This is the historical build log** (Refactor R3): how the app was built, phase by phase —
> the version history, setup (Part A), the phase prompts (Part C), the acceptance checklist
> (D.1) and ideas for later (D.5). The current documentation is elsewhere: start at the
> [README](../README.md). [Requirements](requirements.md), [architecture](architecture.md),
> [decisions](decisions/README.md) and [testing](testing.md) are the source of truth; the B.x
> and D.2–D.4 headings below only point there. Every change is listed in the
> [CHANGELOG](../CHANGELOG.md).

- **Audience:** You (the project owner), building the app with Claude Code inside the Google Antigravity IDE
- **Target:** A web application that runs entirely on your Mac (localhost), with local databases
- **Version:** 4.1 — October 30, 2026 (Refactor R3: documentation split; version 1 of the app was complete at 2.3, Phases 0–12)

### What changed

| Version | Change | Details |
|---|---|---|
| 4.1 | **Refactor R3 – Documentation a new team member can use (docs only)** | This guide is split into [architecture](architecture.md), [requirements](requirements.md), [decisions](decisions/README.md) (one file per decision), [testing](testing.md), [runbooks](runbooks/) and [user guides](user-guides/); new [CHANGELOG](../CHANGELOG.md), [CONTRIBUTING](../CONTRIBUTING.md) and [LICENSE](../LICENSE); a short README; CLAUDE.md points at the new docs. The guide keeps its history (What changed, Build progress, Part A, Part C, D.1, D.5); every moved section keeps its heading with a link. No code, template, migration or settings change |
| 4.0 | **Refactor R2 – Own apps for projects, pay and reports; all apps in apps/ (no change in behaviour)** | Three new apps: **projects** (Project, Task, allowed tasks, budgets; their services and Admin), **compensation** (pay records, the Pay pages and Pay CSV, the salary permission helpers) and **reports** (Project hours and Project budget with their downloads). Every app now lives in `apps/` and is imported as `apps.<app>`, keeping its label, so tables, migrations and audit names are unchanged. Each app keeps its own templates and JavaScript (`apps/<app>/templates/<app>/`, `apps/<app>/static/<app>/`); only site-wide files stay at the top. Four state-only migrations (`projects/0001`, `timesheets/0010`, `compensation/0001`, `directory/0004`) move the models without touching a table or a row. Same pages, URLs and URL names, permissions, numbers, downloads and audit rows; the Admin pages of projects and tasks are now under Admin → Projects (`/admin/projects/…`) and the JS files are served from `/static/<app>/…`. Same 350 tests; coverage 98.25 % before, 98.27 % after (D-174) |
| 3.9 | **Refactor R1 – Reorganized for long-term maintenance (no change in behaviour)** | Same pages, URLs, permissions, rules, tables, migrations, numbers and files. Settings are a package (`config/settings/`: base, local — the default — test for pytest, and a production skeleton that is not used yet); `apps/timesheets/views/` and `apps/analytics/views/` packages replace the `*_views.py` files; the largest services are packages that re-export their public names (`apps/directory/services/demo/`, `apps/reports/services/project_report/`, `apps/payroll/services/register/`; "who still has to approve" moved to `apps/timesheets/services/pending.py`); tests are grouped by app in `tests/<app>/unit` and `tests/<app>/integration`, with `tests/site/` for whole-site checks and one browser-test file per area; a `Makefile` with everyday commands. Before and after: the same 350 tests (270 catalogued IDs); coverage 98.24 % before, 98.25 % after (D-173) |
| 3.8 | **Change 12 – Employee pay, project budgets and labour cost** | HR records each person's **pay** in Admin (admins only): **Salaried** (annual salary + the hourly rate HR fixes, suggested as salary ÷ 2,080) or **Hourly**, each with an "effective from" date. Pay is **history**: a change — or a correction for the same date — is a new record, never an edit; back-dated changes are allowed (not before the hire date) and re-price work from that date; every change is audited. An admin-only **Pay CSV** exports the history and imports new records (preview, line-numbered errors, all-or-nothing). Projects get an optional **budget** (USD) and "costs count from" date. New **Reports → Project budget** for managers (their tree), payroll and HR (everyone): per project the budget, total cost to date (the whole project's approved labour cost), remaining, % used, status (On track / At risk / Over budget / No budget set), cost and hours this period; cost by team or manager, task, pay type and pay period; **By employee** with hourly rate and cost; the **Rate missing** list (hours with no pay record, never costed at $0). Approved hours only; overtime at the same rate (no premium). Two separate downloads: the **costs** file (Excel / CSV) and the Change 11 **hours** file. Migrations `directory/0003_payrecord`, `timesheets/0009_project_budget`; payroll unchanged (D-166–D-172, T-258–T-270) |
| 3.7 | **Change 11b – Only the report filters that make a difference** | On Reports → Project hours a manager now sees only the choices that change the result: **People** (whole tree / direct reports / one manager's group) only when someone under them manages people too; **Group by** only when both Team (people in more than one team) and Manager (more than one manager row) apply — otherwise the one that applies is used and its table shown, and no group table at all when neither does. The Excel skips the same one-row tabs. An address with an option that isn't offered falls back to the default (no error, nobody extra). Directors and admins see what they saw before. No migration (D-165, T-254–T-257) |
| 3.6 | **Change 11 – Reports → Project hours** | A new **Reports** menu item for everyone opens **Project hours** (`/reports/project-hours/`). Filters (kept in the address, so a link can be shared): **Period** (this / last pay period, last 4 or 12 weeks, custom dates widened to whole Sunday–Saturday weeks), **Projects** (the 10b search box; several; inactive projects too), **Hours** (Approved / Approved + Submitted / Everything entered). Employees — payroll-only users too — see only their own hours; managers their tree, directors all their managers' groups, admins everyone, with **People** (whole tree / direct reports / one manager's group) and **Group by** (team or manager). It shows a Summary (project hours, non-project time "not filtered by project", total time, "X with hours of Y people"), By project (with a bar chart), By task, Project × task, By week, Non-project time, and for managers By team or **By manager** (own group + "including everyone below", click to drill in) and **By employee** (everyone in scope, 0.00 rows with a note, leave for context). **Excel** (tabs by role) and **CSV** (one row per counted entry, no reasons) downloads, formula-safe, each written to the audit log. Same numbers everywhere from one service; 9 database reads whatever the size. New package `openpyxl`. No migration (D-160–D-164, T-244–T-253) |
| 3.5 | **Change 10b – Project I-codes and project search** | Project codes are **I-001, I-002, …** (capital I, hyphen, at least 3 digits; I-1000 after I-999), **assigned by the app** when HR adds a project — the next number after the highest ever used, never reused, never edited; HR only types the name. Charge codes are therefore I-001-DEV. In "+ Add row" and ⋮ Change row the Project drop-down is now a **search box**: type part of an I-code or name ("i-00", "001", "portal"), choose with ↑/↓ and Enter or a click; an empty box shows **"Your recent projects"** (the week owner's, from the 4 weeks before the week) and then all active projects, everything sorted by I-code; "No matching project" when nothing fits. The same in the employee grid, Edit directly and the Approvals edit. Migration `timesheets/0008_project_i_codes` adds the project number and renames existing PRJ-xxx codes to I-xxx (audit rows untouched); `seed_demo` uses I-codes from the start. Payroll unchanged (D-155–D-159, T-238–T-243) |
| 3.4 | **Change 10 – Project tasks and charge codes** | Project work is booked to a project **and a task** (9 standard tasks: PLN, DES, DEV, TST, REL, SUP, SEC, DOC, MTG; admins add more, never delete, deactivate instead). Admins tick each project's **Allowed tasks** (a new project starts with all active ones). The **charge code** "I-001-DEV" is worked out, never stored, and shown on every grid row ("I-001 Customer Portal · DEV Development") and in messages. **+ Add row** asks for the project, then one of its tasks; the ⋮ menu's **Change row** can change the task (merging rows as before). Older project work keeps no task ("Task not recorded") and needs one when its week is saved again. Dashboard and Team add **Hours by task** and **Hours by project + task**. Payroll is unchanged. Migrations `timesheets/0006_tasks` (schema) and `0007_default_tasks` (the 9 tasks, linked to every existing project); nothing in the payroll database (D-148–D-154, T-227–T-237) |
| 3.3 | **README & first-run checks** | The README starts with a 10-minute Quick start (with the result to expect after each command), then Updating, Troubleshooting and a developers section. `doctor.sh` answers separately "Ready to RUN the app" (Git, uv, Python 3.13, port 8000) and "Ready to BUILD with Claude Code" (warnings only) and works on Linux. The example `DJANGO_SECRET_KEY` (or one under 50 characters) is a system-check warning while developing and an error for daily use; `seed_demo` refuses the example `DEMO_PASSWORD` (D-145–D-147, T-225, T-226) |
| 3.2 | **Change 9 – Managers decide everyone; payroll waits for everyone** | On Approvals the manager can now **edit, approve or reject** every required person whose weeks are **submitted or locked** (not only submitted): Edit opens the week in the weekly grid (no change request needed); Approve with a locked week asks for a confirmation ("Week 1 was not submitted by …; it will be approved with X.XX hours", with 0.00 / missing-day warnings). Such weeks are marked **"Not submitted by employee"** and still count as missed. A reopened week waits for the employee until its window ends. A register is **READY only when everyone is approved** — the deadline is just a reminder (Overdue); no more 0.00 lines; while OPEN payroll sees only progress and who is pending. New **Pending approvals by manager** page (+ CSV) for payroll and HR. No migration (D-139–D-144, T-217–T-224) |
| 3.1 | **Change 8 – Pay Period Register** | Each ended pay period has a **register**: one line per employee with Week 1, Week 2 and Period hours (regular, overtime, PTO, sick, holiday), highlighted **carry-forward** columns (corrections to already-paid weeks and weeks approved after their register was finalized, with the original weeks) and **Pay total**, plus a totals row. It is a live preview while **OPEN**, **READY** once everyone is approved or the managers' **approval deadline** (new setting, Monday 12:00 after the period) has passed, then **Finalize & export** saves it for good as one batch and **Mark as paid** closes it. People not approved by then get a 0.00 line. Register CSV, detailed CSV and "Download all periods"; the old any-time Export button is gone. New payroll tables (migration `payroll/0003`), `build_registers` for earlier exports; the Approvals page shows the deadline and "Overdue" (D-132–D-138, T-203–T-216) |
| 3.0 | **Change 7 – Edit or delete a whole row** | Each row of an editable grid (the employee's own open week, the manager's Edit directly) has a "⋮" menu: **Change project / category** moves every slot of the row to another project or category (dates, times and reasons kept; into a row that already exists they merge; work ↔ Break allowed with a warning, leave only to another leave type) and **Delete row** removes the row's slots for this week after a confirmation that says how many slots and hours. The server re-draws the grid as typed; nothing is saved until the week is saved, so every rule, the audit row and pay adjustments work as before. No schema change. *Fix before release:* the menu opens from the start of ⋮, on top of the table, and `/static/` files are revalidated on every page load so a browser never runs a new page with cached old CSS/JS (D-129–D-131, T-191–T-202) |
| 2.9 | **Change 6 – Optional reason on time entries** | The Reason field stays in every time-slot dialog (employee grid and Edit directly) but may be left empty; an empty reason is saved as blank and read-only views show a Reason column only when a slot has one. All other entry rules unchanged; change-request reasons and rejection comments stay required. Migration `timesheets/0005` (no database column changes) (D-128, T-187–T-190) |
| 2.8 | **Change 5 – Easier multiple time slots** | "+ Add row" for a project or category that already has a row no longer shows an error: it points at the existing row (scrolled to, highlighted, first day focused) and explains how to add another time slot; a work or Break cell that already has slots opens with them listed plus an empty new slot, ready to fill, and a clearly visible "+ Add another time slot" button; a cell with more than one slot shows "8.00 · 2 slots", with the slot times as its tooltip. Still one row per project or category; rules, validation and data unchanged; no migration (D-127, T-183–T-186) |
| 2.7 | **Change 4 – Automatic pay adjustments** | A corrected week that was already exported or paid is no longer exported again in full: its new version is SETTLED and the difference (regular, overtime, PTO, sick, holiday, total; positive or negative) becomes a pay adjustment carried forward to the next unexported pay run, exported in the same CSV batch as a row of type ADJUSTMENT and paid with it; Corrections shows each adjustment and its status; sync_payroll creates missing ones (D-118–D-126, T-173–T-181) |
| 2.6 | **Change 3 – Sunday-to-Saturday week** | Weeks run Sunday → Saturday and are identified by their Sunday; the Saturday 12:00 deadline is now the last day of the week; pay periods are anchored on Sunday 2026-01-04 and a non-Sunday anchor stops the app; working days stay Mon–Fri; non-Sunday week links redirect; demo data rebuilt by the owner (D-111–D-117, T-168–T-172) |
| 2.5 | **Change 2 – Weekly grid** | Timesheets are entered and shown as a weekly grid: one row per Project / Category, day cells (Sun–Sat since Change 3) with time slots in an accessible dialog, a Total worked hours column and footer; used on the week page, Edit directly, and read-only on submitted weeks, change requests, approvals and the Team week view. Same entries, rules, services and totals; no migration (D-106–D-110, T-160–T-167) |
| 2.4 | **Change 1 – Modern UI** | Light, modern look on every page with one theme stylesheet (`static/css/theme.css`, design tokens), a shared status badge component, centered login/sign-up/profile/error cards, chart colours from the tokens, and a screenshot tool for visual review (D-100–D-105, T-157–T-159). Behaviour, URLs, permissions and rules unchanged |
| 2.3 | **Version 1 complete** | Phases 0–12 built; decisions D-23–D-99 in B.12; 156 catalogued tests (T-01–T-156) including 10 Playwright e2e flows, all passing (status table in B.11); e2e mandatory in `test_all.sh` |
| 2.2 | **Decisions log** | New **section B.12** (D-01…D-22) settles the open points from the spec review. B.1–B.11 and Part C updated to match; **B.12 wins** if anything still conflicts |
| 2.1 | **Payroll database** | Approved hours per week are copied into a **separate payroll database**. Only the new **Payroll** role (and admins) can see and export it (B.4 FR-11, B.6, Phase 8) |
| 2.1 | **Full testing plan** | New **section B.11**: test tools, folder layout, 40+ named test cases, example test code, coverage targets, and a one-command test runner. Tests use their own temporary databases |
| 2.1 | **Bigger demo data** | ~50 employees across 6 departments; most already have accounts and 12 weeks of timesheet history; approved weeks already in the payroll database; a few employees left without accounts to test sign-up (B.7) |
| 2.1 | **Password security** | Passwords are stored with **Argon2 hashing** — one-way protection that nobody, including admins, can reverse (B.4 FR-2, B.10) |
| 2.1 | Copy-safe commands | Part A checks are now short commands, so they copy correctly from the PDF |
| 2.0 | Tech stack | Switched to **Python + Django** |
| 2.0 | Notifications | Not included in version 1 |

### Build progress

| Phase | What | Commit | Status |
|---|---|---|---|
| 0 | Environment check (`doctor.sh`) | (starter kit) | Done |
| 1 | Project scaffold, two databases, Argon2, test setup | `9a54543` | Done |
| 2 | Data model, `import_employees`, `seed_demo`, view-only admin | `ca271e8` | Done |
| 3 | Login, sign-up with directory check, axes lockout | `09cc388` | Done |
| 4 | Layout, profile and permissions | `8c00a4b` | Done |
| 5 / 5b | Weekly timesheet, deadline, validation; start/end times, reasons, Break | `79d8314`, `abce157` | Done |
| 6 | Change requests, unlock, Edit directly | `c7a2ea6` | Done |
| 7 | Biweekly approvals, reject, unlock, bulk approve | `b46bb87` | Done |
| 8 | Payroll database, publish/supersede, export, sync, backup | `e1833ba` | Done |
| 9 | Personal analytics dashboard | `1ca56d5` | Done |
| 10 | Team (hierarchy) analytics | `31aa771` | Done |
| 11 | Admin polish: audited edits, deactivate, password reset, CSV | `f8513b8` | Done |
| 12 | Full test pass, e2e, hardening, README | `bad0b31` | Done |
| Change 1 | Modern UI (post-release, like Phase 5b) | `7f19f32` | Done |
| Change 2 | Weekly grid (post-release) | `39485cd` (with Change 3) | Done |
| Change 3 | Sunday-to-Saturday week (post-release) | `39485cd` (with Change 2) | Done |
| Change 4 | Automatic pay adjustments (post-release) | `fc2606b` | Done |
| Change 5 | Easier multiple time slots in the weekly grid (post-release) | `40e2f07` | Done |
| Change 6 | Optional reason on time entries (post-release) | `23439ce` (with Change 7) | Done |
| Change 7 | Edit or delete a whole row in the weekly grid (post-release) | `23439ce` | Done |
| Change 8 | Pay Period Register (post-release) | `85f22e2` | Done |
| Change 9 | Managers decide everyone each period; registers wait for everyone (post-release) | `0f34b45` | Done |
| README & first-run checks | Quick start README, doctor.sh run/build split, example secret key and demo password refused (post-release) | `e17cc7d` | Done |
| Change 10 | Project tasks and charge codes (post-release) | `22466dc` | Done |
| Change 10b | Project I-codes and project search (post-release) | `8c00c54` | Done |
| Change 11 | Reports → Project hours with Excel and CSV downloads (post-release) | `23fcc6b` | Done |
| Change 11b | Only the report filters that make a difference (post-release) | `4dd8155` | Done |
| Change 12 | Employee pay, project budgets, labour cost and budget vs cost (post-release) | `062a78f` | Done |
| Refactor R1 | Reorganized code and tests; settings package; Makefile — no behaviour change | `228eae6` | Done |
| Refactor R2 | projects, compensation and reports apps; all apps in apps/; templates and JS per app — no behaviour change | `6421d8e` | Done |
| Refactor R3 | Documentation split into architecture, requirements, decisions, testing, runbooks and user guides; CHANGELOG, CONTRIBUTING, LICENSE — docs only | (commit pending) | Done — ready to commit |

---

## How to use this document

1. **Part A — Setup.** Install and check your Mac's tools.
2. **Part B — Blueprint.** Moved to [requirements](requirements.md), [architecture](architecture.md), [decisions](decisions/README.md) and [testing](testing.md); the headings stay as links.
3. **Part C — Build.** Set up the project in Antigravity and drive Claude Code phase by phase with copy-paste prompts (as used for version 1).
4. **Part D — Run.** The acceptance checklist and ideas for later; running, backups and troubleshooting moved to the [runbooks](runbooks/).

> **Tip for copying commands:** the PDF is for reading. Copy commands from the **.md file** (open it in Antigravity) — long lines stay intact there.

Keep this file inside the project at `docs/BUILD_GUIDE.md` as the record of how the app was built. Since Refactor R3 it is no longer the source of truth (see the note at the top).

---

# PART A — Compatibility & Prerequisites

## A.1 Hardware and OS requirements

| Item | Minimum | Recommended | Why |
|---|---|---|---|
| macOS | 13 Ventura | 14 Sonoma or newer | Claude Code's native installer targets macOS 13+; Antigravity needs macOS 12+ |
| Chip | Apple Silicon (M1+) | Apple Silicon | Antigravity's official builds are aimed at Apple Silicon |
| RAM | 8 GB | 16 GB+ | IDE + AI agent + dev server + browser together |
| Free disk | 5 GB | 10 GB+ | Python environment, databases, browser for tests, IDE caches |
| Internet | Needed for setup and Claude Code | — | The **app itself** runs offline once built |

## A.2 Accounts

| Account | Purpose | Status / notes |
|---|---|---|
| Google account + Antigravity subscription | Sign in to Antigravity | ✅ You have this. Use **Claude Code** as the only agent that edits this project |
| Claude **Pro** (or Max) | Claude Code in the terminal and in Antigravity | ✅ Pro is enough. Usage limits are shared with the Claude app (a 5-hour limit plus a weekly limit). The free Claude plan does **not** include Claude Code |
| GitHub (optional) | Online backup of your code | Not required to build or run the app |

> **Important:** Do **not** set an `ANTHROPIC_API_KEY` environment variable on your Mac. If it exists, Claude Code bills that API key instead of your Pro subscription.

## A.3 Software — check first, install only if missing

For each tool, run the **Check** command and compare with **"Installed if…"**. Only run **Install** when it isn't installed.

| # | Tool | Check | Installed if… | Install |
|---|---|---|---|---|
| 1 | Xcode Command Line Tools | `xcode-select -p` | It prints a path | `xcode-select --install` (click **Install** in the pop-up, wait to finish) |
| 2 | Homebrew | `brew --version` | It prints `Homebrew 4.x` | See below |
| 3a | uv | `uv --version` | It prints `uv 0.x` | `brew install uv` |
| 3b | Python 3.13 | `uv python find 3.13` | It prints a path to a Python file | `uv python install 3.13` (`uv sync` also installs it, from `.python-version`) |
| 4 | Git | `git --version` | It prints a version | Comes with step 1 |
| 5 | SQLite CLI (optional) | `sqlite3 --version` | It prints a version | `brew install sqlite` |
| 6 | Antigravity | `ls -d /Applications/Antigravity.app` | It prints `/Applications/Antigravity.app` | Download from **antigravity.google/download** (Apple Silicon), or `brew install --cask antigravity` |
| 7 | Claude Code CLI | `claude --version` | It prints a version | See below |
| 8 | Claude Code extension | In Antigravity: **Cmd+Shift+X**, search `@installed claude` | "Claude Code" by Anthropic is listed | Search **Claude Code** → **Install** → **Cmd+Shift+P** → **Developer: Reload Window** |

**If a check prints an error** such as `command not found` or `No interpreter found`, that tool isn't installed.

### Homebrew install
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
It asks for your Mac password (nothing shows as you type — normal). At the end it prints **"Next steps"** — run those lines. If `brew --version` fails but `ls /opt/homebrew/bin/brew` prints a path, Homebrew is installed and you only need the "Next steps" lines.

### Claude Code install and login
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
Then open a **new** Terminal window.

Run `claude`. If it opens straight to a prompt, you're logged in (type `/exit`). If it asks how to log in, choose your Claude account and finish in the browser.

### Git identity and the home-folder check
Step 1 — your home folder must **not** be a Git repository:
```bash
cd ~
git rev-parse --show-toplevel
```
✅ Good: `fatal: not a git repository`. ⚠️ If it prints `/Users/<you>`, fix it (renames a hidden folder; deletes nothing):
```bash
mv ~/.git ~/.git-backup-old
```
Step 2 — check your identity:
```bash
git config --show-origin user.name
git config --show-origin user.email
```
✅ Good: both lines start with `file:/Users/<you>/.gitconfig`. To set them:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

> **Known quirk:** Antigravity is a VS Code fork, and the `claude` CLI sometimes tries to auto-install its extension using VS Code's `code` command, which Antigravity doesn't have. An error like *"code: command not found"* is harmless if you installed the extension manually (step 8). You can always run `claude` in Antigravity's terminal (**View → Terminal**).

> Node.js is **not needed** for the Django version (fine to leave installed).

## A.4 Environment check script (`doctor.sh`)

The separate file **doctor.sh** runs every check above at once. Save it to Downloads and run:
```bash
bash ~/Downloads/doctor.sh
```
It gives two answers (D-147). ⚠️ = review; ❌ = must fix.
- **"✅ Ready to RUN the app."** This needs only Git, uv, Python 3.13 (via uv) and a free port 8000. Anything missing here is ❌, and the script exits with an error.
- **"✅ Ready to BUILD with Claude Code."** This needs Claude Code (with `ANTHROPIC_API_KEY` **not** set), your Git name and email, a home folder that isn't a Git repository, and on a Mac the Xcode Command Line Tools, Homebrew and Antigravity. These are only needed to change the app, so missing ones are ⚠️ warnings, never failures.

It also shows information about the computer: macOS version, chip, RAM and free disk; the SQLite CLI is optional. On Linux the macOS-only checks are skipped. Run it before starting and again after installing anything. Phase 0 copies it into the project as `scripts/doctor.sh`.

---

# PART B — Requirements Specification (the blueprint)

Every section of Part B moved in Refactor R3; the headings stay because code, scripts and decisions cite them (e.g. "B.7", "B.11").

## B.1 Decisions & defaults

**Moved (Refactor R3):** see [Requirements → Defaults](requirements.md#defaults); the `.env` settings are in [architecture → Settings and configuration](architecture.md#settings-and-configuration).

## B.2 Tech stack

**Moved (Refactor R3):** see [Architecture → Tech stack](architecture.md#tech-stack).

## B.3 Roles & permissions

**Moved (Refactor R3):** see [Requirements → Roles and permissions](requirements.md#roles-and-permissions); how they are enforced: [architecture → Permissions](architecture.md#permissions).

## B.4 Features (your requirements, made precise)

**Moved (Refactor R3):** see [Requirements → Features (FR-1 … FR-13)](requirements.md#features).

## B.5 Timesheet status flow

**Moved (Refactor R3):** see [Requirements → Timesheet status flow](requirements.md#timesheet-status-flow); diagram: [architecture → Timesheet status flow](architecture.md#timesheet-status-flow).

## B.6 Data model

**Moved (Refactor R3):** see [Architecture → Data model](architecture.md#data-model); field by field: each app's `models.py`.

## B.7 Demo data (bigger, realistic, repeatable)

**Moved (Refactor R3):** see [Runbook → Demo data](runbooks/demo-data.md).

## B.8 Pages

**Moved (Refactor R3):** see [Architecture → Pages](architecture.md#pages).

## B.9 Core business logic (plain Python functions)

**Moved (Refactor R3):** see [Architecture → Every core function](architecture.md#every-core-function).

## B.10 Quality rules

**Moved (Refactor R3):** see [Requirements → Quality rules](requirements.md#quality-rules).

## B.11 Testing strategy (NEW)

**Moved (Refactor R3):** see [Testing](testing.md); every catalogued test T-01 … T-270, how to run them and how to write new ones.

## B.12 Decisions log

**Moved (Refactor R3):** see [Decisions](decisions/README.md); one file per decision, D-01 … D-174.

# PART C — Building with Claude Code in Antigravity

## C.1 Create the project folder

```bash
mkdir -p ~/Documents/timesheet-app
cd ~/Documents/timesheet-app
git init
git rev-parse --show-toplevel
```
The last line must print `/Users/<you>/Documents/timesheet-app`. Then:
```bash
mkdir -p docs data scripts
cp ~/Downloads/TIMESHEET_APP_BUILD_GUIDE.md docs/BUILD_GUIDE.md
cp ~/Downloads/doctor.sh scripts/doctor.sh
```
In Antigravity: **File → Open Folder → `~/Documents/timesheet-app`**.

## C.2 Create `CLAUDE.md` in the project root

Claude Code reads this automatically at the start of every session.

```markdown
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
- Every app uses a services package: <app>/services/<module>.py (e.g. apps/payroll/services/publish.py,
  apps/analytics/services/metrics.py); never a single services.py. Business rules live there as plain,
  tested functions. Views stay thin.
- Every view enforces permissions server-side via apps/directory/services/permissions.py.
- Payroll models live only in the payroll database; no foreign keys across databases; payroll
  records are append-only as defined in B.12 D-15 (supersede, never edit). publish_period must be idempotent.
- Passwords: Argon2 first in PASSWORD_HASHERS; never log, print or store plain passwords.
- Durations are integer minutes; work dates are DateField; deadlines computed in COMPANY_TZ.
- Use TextChoices for all statuses. Every manager/admin/payroll action writes an AuditLog row
  (system actions use system_actor instead of actor, D-14).
- Project work is booked to a project and a task (D-148–D-152): the task rule lives only in
  apps/timesheets/services/validation.py with apps/projects/services/tasks.py; the charge code
  "<project>-<task>" is computed by tasks.charge_code, never stored. Payroll never sees tasks.
- Project codes are I-001, I-002, … (D-155): assigned only by apps/projects/services/projects.py
  (assign_code, never typed or edited, never reused) and sorted by Project.number, never as text.
  Project search matching lives only in projects.search_projects (D-157).
- Reports → Project hours (D-160–D-164): every number comes from
  apps/reports/services/project_report.py (page, Excel and CSV alike; who is in it only from
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
- Tests: follow docs/BUILD_GUIDE.md B.11 (layout, test IDs T-01 onward, factories, fixed clock).
  Every new rule gets tests in the same phase. New catalogued tests continue at T-43 and are added
  to the B.11 table (D-16). Each catalogued test's docstring starts with its ID (D-17).
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
```

Then make the first commit yourself **before Phase 0** (D-05):
```bash
git add -A
git commit -m "Initial docs"
```

## C.3 Working rhythm with Claude Code

- **Plan before code.** Start each phase in *Plan mode* (`Shift+Tab` cycles modes in the CLI; the extension has a mode selector). Read the plan, then let it implement.
- **One phase per conversation.** After committing a phase, type `/clear`. Use `/compact` if a phase runs long.
- **Protect your Pro usage.** Usage is shared with the Claude app. If you hit the 5-hour limit, stop and continue later.
- **Review every change** before accepting it. Ask "why?" whenever something looks surprising.
- **Test, then commit after every phase:**
  ```bash
  bash scripts/test_all.sh
  git add -A
  git commit -m "Phase N: <short description>"
  ```
- **Undo a bad phase:** `git restore .` then `git clean -fd` (removes new, uncommitted files — use with care).
- **Report bugs precisely:** paste the exact error text and the steps that caused it.

## C.4 Phase-by-phase prompts (copy and paste into Claude Code)

### Phase 0 — Environment check
```
Read CLAUDE.md and docs/BUILD_GUIDE.md Part A. Make scripts/doctor.sh executable, run it, and explain
any ❌ or ⚠️ items and how to fix them. Do not create the Django project yet.
```
✅ Verify: ends with "✅ Ready to RUN the app." and "✅ Ready to BUILD with Claude Code."

### Phase 1 — Project scaffold + test setup
```
Plan first, then scaffold the project in the current folder:
- uv project pinned to Python 3.13; add django ">=5.2,<5.3", django-environ, argon2-cffi, django-axes,
  faker; dev deps: pytest, pytest-django, factory-boy, time-machine, pytest-cov,
  pytest-playwright, ruff.
- Django project package "config"; apps: directory, timesheets, audit, payroll, analytics, each with
  a services/ package (D-04).
- Two databases (default → db.sqlite3, payroll → payroll.sqlite3) and apps/payroll/routers.py as in B.6.
- Custom User model (directory.User) with Team and Employee models exactly as in B.6 (including
  end_date), with AUTH_USER_MODEL set BEFORE the first migrate. Custom UserManager and the
  createsuperuser employee_code flow (D-02). apps/directory/services/accounts.py sync_account called on
  every Employee save (D-13, D-20).
- PASSWORD_HASHERS with Argon2PasswordHasher first; password validators with min length 12.
- Settings from .env via django-environ; .env.example with every variable from B.1, including
  DJANGO_ALLOWED_HOSTS (D-03); TIME_ZONE from COMPANY_TZ, USE_TZ=True.
- Vendor Bootstrap 5, HTMX and Chart.js into static/vendor/. base.html and a placeholder home page.
- Test setup from B.11: tests/ folders, conftest.py, factories.py, pytest markers (e2e), coverage config,
  and scripts/test_all.sh with the e2e skip rule (D-01). Write T-06, T-07, T-08 now (password hashing
  tests), plus new catalogued tests (T-43 onward, D-16) for D-02, D-13 and D-20.
- ruff config, .gitignore (.env, *.sqlite3, .venv, backups/, htmlcov/), README.md.
Migrate both databases, run the tests, then tell me how to start the server.
```
✅ Verify: copy `.env.example` to `.env` and fill in values. Generate a secret key with:
```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(50))"
```
Then `uv run python manage.py runserver` and open http://127.0.0.1:8000.

### Phase 2 — Data model & demo data
```
Implement the remaining main-database models from B.6 (timesheets, audit — AuditLog with nullable
actor, system_actor and the exactly-one constraint, D-14) and migrations.
Management commands:
- import_employees <csv>: upsert by employee_code (teams created; managers linked in a second pass;
  is_admin, is_payroll, status columns; optional end_date column, D-19).
- seed_demo exactly as described in B.7: data/employees_core.csv (13 core employees), ~37 Faker
  employees with a fixed seed, accounts for all active employees except qa1, ops1, ops2, passwords
  from DEMO_PASSWORD set with set_password (Argon2), 8 projects, 12 weeks of history with the mix
  described, refuse to run if data already exists. --large option (~500 employees, 52 weeks).
  Approve only periods whose two weeks are SUBMITTED (D-06); audit rows the seed itself creates use
  system_actor="seed_demo" (D-14). (Payroll records are added to the seed in Phase 8.)
Register models in Django Admin (AuditLog read-only). Tests: T-41 (without payroll part), T-42,
plus import_employees tests and a new catalogued test for D-14.
```
✅ Verify: `uv run python manage.py seed_demo`, then log in at http://127.0.0.1:8000/admin/ as `hr@yourcompany.com` and browse employees and timesheets. Open any user — the password shows as an Argon2 hash, not the real password.

### Phase 3 — Login & sign-up with directory check
```
Implement FR-1 and FR-2: /login/, /signup/, /logout/ with Bootstrap pages.
Eligibility rules in apps/directory/services/signup.py. Configure django-axes (5 failures → 15-minute lock).
Require login everywhere except login and signup. Inactive employees cannot log in.
Directory admins get is_staff and is_superuser through the D-13 sync (built in Phase 1).
Tests: T-01 to T-05 and T-09 to T-11.
```
✅ Verify: sign-up works for `qa1@yourcompany.com`; refused for `nobody@yourcompany.com`, `former@yourcompany.com` and `dev1@gmail.com`; `dev1@yourcompany.com` says the account already exists.

### Phase 4 — App layout, profile & permissions
```
Build the logged-in layout: navbar with name, Employee ID, job title and team (FR-4); menu: Dashboard,
Timesheets, Requests for everyone; Team and Approvals only for managers; Payroll only for payroll/admin;
Admin link only for admins. /profile/ with password change.
apps/directory/services/permissions.py: reporting_tree (cycle-safe), is_manager, can_view, can_approve,
can_edit, can_access_payroll, plus view decorators/mixins. can_approve per D-11 (never self; admins
only for employees with no manager); roles add up and the payroll flag grants nothing beyond /payroll/
(D-12). Tests: T-26, T-27, T-28, plus new catalogued tests for D-11 and D-12.
```
✅ Verify: `dev1` sees no Team/Approvals/Payroll; `eng.manager` sees Team and Approvals; `payroll` sees Payroll.

### Phase 5 — Weekly timesheet & deadline
```
Implement FR-8 and /timesheets/ and /timesheets/<YYYY-MM-DD>/: one row per entry (date, category,
project, start/end time or leave hours, reason (optional since D-128); unlimited rows, D-35–D-43), 15-minute steps, live
day summary with HTMX, Save draft, Submit, deadline countdown.
Calendar logic in apps/timesheets/services/calendar.py, validation in apps/timesheets/services/validation.py.
Weekend hours can be entered in advance (D-09). PROJECT entries need an active project, other
categories none (D-18). Entries only within hire_date…end_date; expected_minutes_for prorates
partial weeks; weeks outside employment are never missed (D-19).
"now" is a parameter so tests control the clock. Tests: T-12 to T-22, plus new catalogued tests for
D-18 and D-19.
```
✅ Verify: fill in and submit this week — it becomes read-only. A past unsubmitted week shows LOCKED.

### Phase 6 — Change requests & manager edits
```
Implement FR-9: Request change; /requests/; /approvals/requests/ with Reject, Unlock (window per D-21) and
Edit directly; AuditLog with before/after for every manager/admin change; editing a week in an approved
period resets that PeriodApproval to PENDING through apps/timesheets/services/approvals.py in one
transaction (D-10) (leave a clear hook for the payroll "supersede" step, implemented in Phase 8).
reopen_until = the later of +48 h and the week's Saturday 12:00 deadline (D-21); an unused window
makes the week LOCKED; late resubmissions keep is_late (D-08).
Open-request count in the managers' menu. Tests: T-23 to T-25, T-43, plus new catalogued tests for D-08.
```
✅ Verify: dev1 requests a change → eng.manager edits it → the audit log in /admin/ shows before/after.

### Phase 7 — Biweekly approvals
```
Implement FR-7: /approvals/ with pay-period picker and one row per direct report; detail page to approve
or reject (comment required); bulk approve for rows without flags; admins approve employees with no
manager, never themselves (D-11). Only SUBMITTED weeks can be approved; LOCKED weeks get an Unlock
button that creates a manager-authored ChangeRequest + audit entry (D-06). Reject → REOPENED with
reopen_until per D-21 (D-07). Logic in apps/timesheets/services/approvals.py, the only code that moves
weeks to/from APPROVED (D-10). Tests: T-29 to T-32, plus new catalogued tests for D-06, D-07, D-10, D-11.
```
✅ Verify: as eng.manager, approve the pending period for dev2 and reject one for dev1; dev1 sees the comment and can resubmit.

### Phase 8 — Payroll database (NEW)
```
Implement FR-11 and the payroll app (models only in the payroll database, as in B.6):
- apps/payroll/services/ package (D-04): hours.py split_hours (overtime rule from B.1 row 16; Break time
  excluded from regular hours and overtime, D-45);
  publish.py publish_period (idempotent), supersede_week; export.py export_period (CSV + batch number),
  mark_paid. Call publish_period after approval; call supersede_week from the Phase 6 hook.
- Append-only per D-15: frozen snapshot/hours fields, forward-only status changes, enforced in code.
- Deactivated employees' existing timesheets can still be approved and paid (D-19).
- sync_payroll management command that re-checks all approved periods.
- /payroll/ (filters, per-employee totals, Export CSV, Mark paid) and /payroll/corrections/,
  for payroll and admin only.
- Required AuditLog rows (D-22): publish → PUBLISH, supersede → SUPERSEDE, export → EXPORT,
  mark paid → PAY, sync_payroll → SYNC (system_actor="sync_payroll", D-14).
- Extend seed_demo to fill the payroll database as described in B.7 (older periods EXPORTED/PAID,
  one SUPERSEDED correction).
- backup_db must back up both databases.
Tests: T-33 to T-39, the payroll part of T-41, plus new catalogued tests for D-15 and D-19.
```
✅ Verify: log in as `payroll@yourcompany.com` → Payroll shows approved weeks with hours split. Approve a period as eng.manager → new weeks appear for payroll. Export CSV opens in Excel/Numbers. Log in as dev1 → `/payroll/` is Forbidden.

### Phase 9 — Personal analytics dashboard
```
Implement FR-5 on the home page with Chart.js. Metrics in apps/analytics/services/metrics.py as tested pure
functions (missed weeks counted only within hire_date…end_date; expected hours prorated for partial
weeks, D-19). Chart data via json_script. Range filter 4/12/26 weeks.
Current-week card with countdown. Test: T-40.
```

### Phase 10 — Team (hierarchy) analytics
```
Implement FR-6 on /team/ and /team/<employee_code>/: whole tree with direct-only toggle, team and date
filters, per-employee table, this week's compliance list, hours by project, drill-down reusing the
dashboard components. Enforce can_view on every query. With the --large seed, pages must load in under
1 second (use select_related/prefetch_related or caching). Add tests for team metrics.
```
✅ Verify: `eng.director` sees Priya **and** her reports; Priya sees only hers; `dev1` gets Forbidden on /team/.

### Phase 11 — Admin polish
```
Finish FR-10 in Django Admin: CSV import/export for Employee, filters and search for employees, teams,
projects and timesheets, a "deactivate" action (sets status INACTIVE and end_date, D-19),
is_admin/is_payroll editing and email changes (User synced per D-13/D-20), password reset (never show
passwords), read-only filterable AuditLog. Only directory admins reach /admin/. Tests for access rules
(new catalogued IDs, D-16).
```

### Phase 12 — Full test pass, hardening & backup
```
Complete B.11: make sure every catalogued test ID (T-01 onward) exists and passes; install Chromium and
remove the e2e skip from scripts/test_all.sh so e2e is mandatory (D-01); write the Playwright E2E tests
(marked e2e) for: sign-up refused/accepted, submit before deadline, locked after deadline (fixed clock),
change request → manager edit, approve → payroll record visible to payroll user, reject, permission
denials. Reach the coverage targets. Run `manage.py check --deploy` and fix what applies to a local app.
Update README.md with setup, run, test and backup instructions. Finish with a table of all test IDs and
their status.
```
✅ Verify:
```bash
uv run playwright install chromium
bash scripts/test_all.sh
```
(The first command is needed only once.)

## C.5 Optional: Claude Code permissions file

Create `.claude/settings.json` to reduce approval prompts for safe commands and block risky ones:
```json
{
  "permissions": {
    "allow": [
      "Bash(uv run pytest*)",
      "Bash(uv run ruff*)",
      "Bash(bash scripts/test_all.sh)",
      "Bash(uv run python manage.py check*)",
      "Bash(uv run python manage.py makemigrations*)",
      "Bash(uv run python manage.py migrate*)",
      "Bash(uv add *)",
      "Bash(git status)",
      "Bash(git diff*)"
    ],
    "deny": [
      "Bash(uv run python manage.py flush*)",
      "Bash(rm -rf*)",
      "Bash(rm *sqlite3*)",
      "Read(./.env)"
    ]
  }
}
```
(If Claude Code's settings format changes, check docs.claude.com.)

---

# PART D — Testing, Running & Maintaining

## D.1 Manual acceptance checklist

Use the [demo logins](runbooks/demo-data.md#logins) (password = `DEMO_PASSWORD`).

| # | Log in as | Scenario | Expected result |
|---|---|---|---|
| 1 | (none) | Sign up `nobody@yourcompany.com` | Refused — "Contact HR" |
| 2 | (none) | Sign up `qa1@yourcompany.com` | Account created; header shows Ravi Kumar, EMP-0006, QA Engineer, Platform |
| 3 | hr | Open the new user in /admin/ | Password shown only as an Argon2 hash |
| 4 | dev2 | Wrong password 5 times | Locked for 15 minutes |
| 5 | dev1 | Add rows with start/end times (a reason is optional, D-128), Save draft, then submit before Saturday 12:00 | SUBMITTED, read-only |
| 6 | dev1 | Look at a past unsubmitted week | LOCKED; counted as missed on dashboard |
| 7 | dev1 → eng.manager | Request change → manager unlocks | dev1 can edit for at least 48 hours (until the later of +48 h and Saturday 12:00, D-21) |
| 8 | eng.manager | Edit a report's week | Audit log entry with before/after values |
| 9 | eng.manager | Approve a biweekly period | Both weeks APPROVED |
| 10 | payroll | Open Payroll → that period's register | Open (with who is still pending) until everyone is approved, then Ready; lines with regular / overtime / PTO hours |
| 11 | payroll | Finalize & export, then Mark as paid | One batch (EXP-xxxx) with Register CSV and Detailed CSV; then the register is Paid |
| 12 | eng.manager | Edit a week in that paid period via change request | Payroll shows it under Corrections |
| 13 | eng.manager | Reject a period with a comment | Both weeks REOPENED; comment visible to the employee |
| 14 | eng.director | Open Team | Sees Priya and her reports |
| 15 | dev1 | Open /team/ and /payroll/ | Forbidden |
| 16 | dev1 | Add a work row 09:00–17:00 and a Break 12:00–12:30 the same day; then make them back-to-back | First refused as overlapping; then saved, and Hours worked excludes the Break (D-38, D-39, D-41) |

## D.2 Daily commands

**Moved (Refactor R3):** see [Runbook → Setup](runbooks/setup.md); everyday commands: `make help`; backups: [backup and restore](runbooks/backup-restore.md).

## D.3 Backups & reset

**Moved (Refactor R3):** see [Runbook → Backup and restore](runbooks/backup-restore.md); starting over with demo data: [demo data → Start over](runbooks/demo-data.md#start-over-with-fresh-demo-data).

## D.4 Troubleshooting

**Moved (Refactor R3):** see [Runbook → Troubleshooting](runbooks/troubleshooting.md).

## D.5 Future enhancements (after version 1)

- **Notifications** — in-app first, then email reminders via a local test mail server (Mailpit)
- Payroll export in your payroll provider's exact file format
- Company single sign-on instead of passwords
- Holiday calendar that pre-fills HOLIDAY entries
- Delegated approvals when a manager is on leave
- Move the payroll database (and then the app) to PostgreSQL on a server

---

## Quick start summary

1. **Part A:** run `doctor.sh` until it says "✅ Ready to RUN the app." and "✅ Ready to BUILD with Claude Code."
2. **Requirements:** review the [defaults](requirements.md#defaults) — especially the overtime rule (row 16).
3. **Part C:** create `~/Documents/timesheet-app`, add `docs/BUILD_GUIDE.md`, `scripts/doctor.sh` and `CLAUDE.md`, open it in Antigravity, then run Phases 0 → 12 — test with `scripts/test_all.sh` and commit after each.
4. **Part D:** walk through the acceptance checklist with the demo logins, and back up both databases regularly.
