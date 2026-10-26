# Employee Timesheet Web App — Local Build Guide
## Python + Django · macOS · Google Antigravity · Claude Code

- **Audience:** You (the project owner), building the app with Claude Code inside the Google Antigravity IDE
- **Target:** A web application that runs entirely on your Mac (localhost), with local databases
- **Version:** 2.3 — October 24, 2026 (version 1 of the app complete: Phases 0–12)

### What changed

| Version | Change | Details |
|---|---|---|
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
| Change 8 | Pay Period Register (post-release) | (commit pending) | Done — ready to commit; run `migrate --database=payroll`, then `build_registers` |

---

## How to use this document

1. **Part A — Setup.** Install and check your Mac's tools.
2. **Part B — Blueprint.** What the app must do. Review the decisions table in B.1.
3. **Part C — Build.** Set up the project in Antigravity and drive Claude Code phase by phase with copy-paste prompts.
4. **Part D — Run.** Test, run, back up, and troubleshoot.

> **Tip for copying commands:** the PDF is for reading. Copy commands from the **.md file** (open it in Antigravity) — long lines stay intact there.

Keep this file inside the project at `docs/BUILD_GUIDE.md` — Claude Code treats it as the source of truth.

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
| 3b | Python 3.12+ | `uv python find '>=3.12'` | It prints a path to a Python file | `uv python install 3.13` |
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
It must end with **"🎉 Ready to build."** (⚠️ = review; ❌ = must fix). Run it before starting and again after installing anything. Phase 0 copies it into the project as `scripts/doctor.sh`.

What it checks: macOS 13+, Apple Silicon, RAM, disk space, Xcode tools, Homebrew, Git, home-folder repository, Git identity, uv, Python 3.12+, SQLite, Claude Code, that `ANTHROPIC_API_KEY` is **not** set, Antigravity, and that port 8000 is free.

---

# PART B — Requirements Specification (the blueprint)

## B.1 Decisions & defaults

"Decided" rows are settled. "Default" rows are sensible choices you can change any time **before** the phase that uses them — edit this table and tell Claude Code.

| # | Topic | Value | Status |
|---|---|---|---|
| 1 | Tech stack | Python + Django | **Decided** |
| 2 | Company email domain | `@yourcompany.com` (fake) — `.env` → `COMPANY_EMAIL_DOMAIN` | **Decided** |
| 3 | Demo data | ~50 fake employees; most with accounts and history (B.7) | **Decided** |
| 4 | Notifications | **Not in version 1** | **Decided** |
| 5 | Payroll data | Approved hours per week copied to a **separate payroll database**, visible only to Payroll and Admin | **Decided** |
| 6 | Password storage | **Argon2** one-way hashing | **Decided** |
| 7 | Testing | Automated tests for every phase + browser tests; see B.11 | **Decided** |
| 8 | Company time zone | `America/Chicago` — `.env` → `COMPANY_TZ` | Default |
| 9 | Work week | **Sunday → Saturday**; a week is identified by its Sunday (D-111; until Change 3: Monday → Sunday) | **Decided** |
| 10 | Weekly deadline | **Saturday 12:00 noon** company time, the last day of the week (D-112). The rest of Saturday may be entered in advance (D-09) | **Decided** |
| 11 | Missed deadline | Week becomes **LOCKED** (missed). It must be unlocked — via the employee's **Change Request** or by the manager from the approval page — and then submitted. An unused reopen window returns the week to LOCKED (D-06, D-08) | **Decided** |
| 12 | Biweekly period | 2 weeks, anchored on **Sunday** `2026-01-04` — `.env` → `PAY_PERIOD_ANCHOR`; must be a Sunday or the app refuses to start (D-113; until Change 3: Monday 2026-01-05) | **Decided** |
| 13 | Approver | **Direct manager**; higher managers view only. Employees with **no manager** are approved by an Admin. **Nobody ever approves their own timesheet** (D-11) | **Decided** |
| 14 | Analytics visibility | Roles add up (D-12). Everyone: own. Manager: + whole reporting tree. Admin: everyone. Payroll flag: adds payroll pages only | **Decided** |
| 15 | Time categories | **Work** (start/end times): Project work, Meetings, Training, Other. **Break time** (start/end times, unpaid, D-39). **Leave** (hours only): PTO, Sick, Holiday (D-37, D-40) | Default |
| 16 | Overtime rule (payroll) | Per week: worked minutes (Project work, Meetings, Training, Other) up to that week's expected minutes (prorated for partial weeks, D-19) are **regular**; the rest is **overtime**. PTO, Sick and Holiday are separate totals and never overtime. **Break is unpaid and never counts anywhere.** Stored as minutes, shown as hours with 2 decimals (D-64, D-45) | Default — confirm with payroll; real overtime rules depend on law and contracts |
| 17 | Hours granularity | 15-minute steps; max 24 h/day; stored as whole minutes | Default |
| 18 | Expected hours | 40 h/week, can differ per employee. Partial weeks (hire / end date) are prorated by active weekdays (D-19) | Default |
| 19 | Email verification at sign-up | Off (directory check only) | Default |

### What `.env` is
`.env` is a small private settings file in the project folder. The app reads values from it instead of hard-coding them, so a setting changes in **one line**. It holds secrets, so it is **never** committed to Git; a safe template, `.env.example`, is committed instead. Claude Code creates both in Phase 1:
```
DJANGO_SECRET_KEY=change-me-to-a-long-random-string
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
COMPANY_EMAIL_DOMAIN=@yourcompany.com
COMPANY_TZ=America/Chicago
PAY_PERIOD_ANCHOR=2026-01-04
DEMO_PASSWORD=choose-a-strong-demo-password
```

## B.2 Tech stack

| Layer | Choice | What it does for us |
|---|---|---|
| Language | **Python 3.13** (3.12+ OK), managed by **uv** | One language for the whole app |
| Framework | **Django 5.2 LTS** | Pages, URLs, forms, server logic; long-term support |
| Databases | **Two SQLite files:** `db.sqlite3` (main app) and `payroll.sqlite3` (payroll) | No server to install; each backed up by copying one file |
| Database tools | **Django ORM + migrations** + a **database router** | Tables defined in Python; the router sends payroll tables to the payroll database |
| Login & security | **Django auth** + **Argon2** (`argon2-cffi`) + **django-axes** | Strong password hashing, sessions, CSRF protection, lockout after 5 failed logins |
| HR admin screens | **Django Admin** | Ready-made screens; employee CSV import/export through our own audited admin views (D-92, D-98) |
| Settings | **django-environ** | Reads `.env` |
| Screens | **Django templates + Bootstrap 5 + HTMX** | Clean responsive pages; no JavaScript build step |
| Charts | **Chart.js** | Analytics charts |
| Time zones | **zoneinfo** (built in) | Correct Saturday-noon deadline, including daylight-saving changes |
| Demo data | **Faker** (fixed seed) | Realistic, repeatable fake employees |
| Tests | **pytest, pytest-django, factory_boy, time-machine, pytest-cov**; **Playwright for Python** | See B.11 |
| Code quality | **Ruff** | Linting and formatting |

Bootstrap, HTMX and Chart.js files are saved inside the project (`static/vendor/`), so the app works fully offline.

## B.3 Roles & permissions

| Capability | Employee | Manager | Payroll | Admin (HR) |
|---|---|---|---|---|
| Sign up / log in with company email | ✅ | ✅ | ✅ | ✅ |
| View own profile | ✅ | ✅ | ✅ | ✅ |
| Enter and submit own weekly timesheet | ✅ | ✅ | ✅ | ✅ |
| View own analytics | ✅ | ✅ | ✅ | ✅ |
| Raise a change request on own week | ✅ | ✅ | ✅ | ✅ |
| View analytics of reporting tree | — | ✅ own tree | — | ✅ everyone |
| Approve / reject biweekly timesheets | — | ✅ direct reports | — | ✅ top-level employees only (never self) |
| Edit a report's week after a change request (audited) | — | ✅ | — | ✅ |
| **View payroll database (approved hours)** | — | — | ✅ | ✅ |
| **Export payroll CSV; mark weeks as paid** | — | — | ✅ | ✅ |
| Manage employees, teams, projects; audit log | — | — | — | ✅ (Django Admin) |

- **Manager** is automatic: anyone with at least one employee reporting to them.
- **Payroll** is the `is_payroll` flag in the employee directory.
- **Admin** is the `is_admin` flag.
- **Roles add up** (D-12). Everyone is an employee first (own timesheet, analytics, change requests). The payroll flag only **adds** `/payroll/` and never grants access to other people's timesheet details. A payroll user who is also a manager gets normal manager rights for their own tree.
- **Nobody ever approves their own timesheet** (D-11). The approver is the direct manager; Admins approve only employees with no manager, never themselves (the CEO is approved by the HR admin).
- `User.is_staff` / `is_superuser` always follow `Employee.is_admin`, and `User.is_active` follows `Employee.status` — kept in sync whenever an Employee is saved (D-13).

## B.4 Features (your requirements, made precise)

**FR-1 Login.** Company email + password. Inactive employees cannot log in (`User.is_active` follows `Employee.status`, D-13). 5 failed attempts → locked for 15 minutes.

**FR-2 Sign-up with directory check and secure password storage.**
1. Email is trimmed and lower-cased; it must end with `COMPANY_EMAIL_DOMAIN`.
2. Email must exist in the **Employee directory** with status ACTIVE.
3. That employee must not already have an account.
4. Pass → account created and linked to the directory record. Fail → *"This email is not in the company employee directory. Contact HR."* or *"An account already exists — please log in."*
5. Password rules: at least 12 characters plus Django's standard checks (not too common, not all numbers, not too similar to the email).
6. **The password is never stored as typed.** It is converted with **Argon2** (a one-way hash with a random "salt") and only that result is saved. At login, the typed password is hashed the same way and compared. Nobody — not admins, not someone with the database file — can read the original password. Forgotten passwords are **reset** by an admin, never shown.
7. Directory admins automatically get Django Admin access, and lose it when `is_admin` is cleared — `is_staff`/`is_superuser` are kept in sync on every Employee save (D-13).
8. The account email always mirrors the directory: `Employee.email` is the source of truth and `User.email` follows it, lower-cased (D-20).

> **Why "hashing" and not "encryption":** encryption can be reversed with a key, so anyone who gets the key can read every password. Hashing cannot be reversed, which is why it is the industry standard for passwords. This meets — and is safer than — "encrypted passwords".

**FR-3 Local databases.** Main data in `db.sqlite3`; payroll data in `payroll.sqlite3`. No cloud services.

**FR-4 Profile from directory.** Header and Profile page show full name, Employee ID, job title, team, department, manager, location, hire date — read-only, from the directory.

**FR-5 Personal analytics (Dashboard).** Rules in B.12 D-74–D-80. Range filter (last 4 / 12 / 26 weeks):
- Hours per week vs expected (bar chart with target line)
- On-time submission rate
- Hours by project and by category
- Overtime hours
- Approval outcomes (approved / rejected / pending)
- **Current-week card** with status and a live countdown to Saturday 12:00 noon

**FR-6 Team analytics (hierarchy).** Rules in B.12 D-81–D-86. For managers (admins: everyone); filters: direct reports vs whole tree, team, date range.
- Team hours per week, average utilization
- Per-employee table: hours, utilization %, on-time rate, late/missed weeks, pending approvals
- This week's compliance: who hasn't submitted yet
- Hours by project across the team
- Click anyone in the tree → read-only view of their analytics and timesheets

**FR-7 Biweekly approvals page.** Pay periods are 14 days, two Sunday→Saturday weeks counted from the Sunday `PAY_PERIOD_ANCHOR` (D-113). For managers (and Admins, for employees with no manager). Nobody sees their own row (D-11). Details settled in B.12 D-54–D-63 (rows and periods, flags, partial weeks, reject, open requests, unlock, resubmission, payroll hook, bulk approve).
- Pick a pay period (default: most recent completed)
- One row per direct report: week 1 and week 2 status, total hours, flags (late, overtime, missing days)
- Open a row → both weeks' entries → **Approve** or **Reject** (comment required)
- Approve **only** when both weeks are SUBMITTED (D-06)
- A LOCKED week shows an **Unlock** button: it creates a manager-authored ChangeRequest (status UNLOCKED) plus an audit entry and reopens the week until `reopen_until` (D-21); the employee then submits (D-06)
- **Bulk approve** for rows with no flags
- Reject → both weeks become REOPENED with `reopen_until` set per D-21, and the manager's comment is shown to the employee (D-07)
- **Reopen window (D-21):** `reopen_until` = the later of (unlock/reject time + 48 hours) and the week's normal Saturday 12:00 deadline

**FR-8 Weekly timesheet and deadline.** Each week is a **weekly grid** (D-106): one row per Project / Category (e.g. "PRJ-001 Customer Portal / Project work", "Meetings", "Break (unpaid)", "PTO"), columns Sun–Sat (the week runs Sunday → Saturday and is identified by its Sunday, D-111) headed with the day and date, then a **Total worked hours** column, and a footer with Total worked hours per day and for the week (work only; Break shown but never counted, leave shown and labelled). "+ Add row" picks a category, and a project for Project work (active projects only; no duplicate rows). On an editable grid each row's "⋮" menu can **change the row's project / category** (all its slots move; merging into an existing row) or **delete the row** for this week (D-129, D-130). Clicking a day cell opens a dialog for that row and day: work and Break cells hold one or more **time slots** (start, end, reason); leave cells hold hours and a reason. Each slot is one entry, as many as needed (D-35, D-107). Every entry has a date, a category, a project (Project work only, D-18) and an optional reason (D-36, optional since D-128). Work rows (Project work, Meetings, Training, Other) and **Break** rows have a start and end time in 15-minute steps on the same day; the hours are calculated from the times (D-37). Timed rows on one day must not overlap (D-38). Leave rows (PTO, Sick, Holiday) have hours only (D-40). Break time is unpaid (D-39). **Hours worked** = work rows only; the page shows it per day and per week next to the expected hours, with separate Break and Leave totals and each day's first start and last end (D-41). Each day's work + Break + leave is at most 24 hours (D-42). A week needs at least one entry to be submitted, and a week with only Break rows cannot be submitted (D-32, D-43). Only the current week and earlier open (D-33). Problems are shown on the cell they belong to and inside its dialog (D-108); the page warns before leaving with unsaved changes (D-110). The same grid is used read-only on submitted, approved and locked weeks, change requests, the approval page and the Team week view (D-109). Submit by **Saturday 12:00 noon** company time. Weekend hours may be entered in advance; any change after submitting goes through a change request (D-09). After submitting: read-only. After the deadline, an unsubmitted week is **LOCKED / missed** (worked out when the page opens, so no background job is needed). When a reopen window (unlock or reject; it ends at the later of +48 hours and the week's Saturday 12:00 deadline, D-21) ends without resubmission, the week becomes LOCKED; a week submitted after its original deadline keeps `is_late = True` (D-08). Weeks with no timesheet at all count as missed only while the person was employed (from `hire_date` to `end_date`); weeks fully outside employment are never missed (D-19).

**FR-9 Manager changes on request.** Rules settled in B.12 D-46–D-53 (which weeks, who handles, notes, edit/unlock behaviour, late flag, payroll hook).
1. Employee opens a submitted or locked week → **Request change** → writes a reason.
2. The manager's **Change Requests** page lists open requests (count shown in the menu).
3. Manager chooses **Reject**, **Unlock for employee** (open until the later of +48 hours and the week's Saturday 12:00 deadline, D-21; if unused, the week becomes LOCKED — D-08), or **Edit directly**.
4. Every manager/admin change creates an **Audit Log** entry: who, when, before and after values, linked request.
5. Editing a week in an approved period sets that approval back to PENDING — done only through `timesheets/services/approvals.py`, in the same transaction (D-10) — and the payroll record for that week is marked **superseded** (see FR-11).

**FR-10 Admin (HR).** Rules in B.12 D-87–D-93. Through Django Admin at `/admin/` (directory admins only): manage employees (CSV import, deactivate, set Payroll/Admin flags), teams, projects; read-only audit log; view all timesheets; reset passwords.

**FR-11 Payroll database (NEW).**
1. When a manager **approves** a biweekly period, the app writes **one payroll record per approved week** into the **separate payroll database**.
2. Each record is a **snapshot** at the moment of approval: Employee ID, name, department, team, week start, period start, **regular hours, overtime hours, PTO, Sick, Holiday, total hours**, expected hours, approver name, approval time.
3. Payroll records are **append-only** (D-15): snapshot and hours fields never change after creation. Only `status`, `export_batch`, `exported_at`, `paid_at` and `superseded_at` may change, and only forward: CURRENT → EXPORTED → PAID, and any status → SUPERSEDED. This is enforced in code and tested. If an approved week is later changed (FR-9), the old record is marked **SUPERSEDED** and, after re-approval, a **new version** is written. Payroll always sees the current version plus a history of corrections. **Pay adjustments (Change 4, D-118–D-126):** if an earlier version of that week was already exported or paid, the new version is **SETTLED** — it is never exported again in full — and the difference (new version − previous version, for regular, overtime, PTO, sick, holiday and total minutes; positive or negative; nothing when zero) becomes a **pay adjustment**: its own append-only record, carried forward to the next pay period that has no export batch yet (D-121) and paid in that run. If the earlier versions were never exported, the new version is exported normally. Timesheets of an employee who has since been deactivated can still be approved and paid (D-19).
4. **Payroll page** (`/payroll/`), for Payroll and Admin only:
   - Filter by pay period, department, team, employee, status
   - Totals per employee per period (regular, overtime, PTO, sick, holiday), plus **Adjustments** carried into the period, Total = weeks + adjustments (D-124)
   - **Export CSV** for the selected period → its CURRENT week records **and** CURRENT adjustments are stamped with one export batch number and marked **EXPORTED**; the CSV has a `row_type` column (WEEK / ADJUSTMENT) and the original week of each adjustment (D-123)
   - **Mark as paid** → the batch's records and adjustments become **PAID**
   - **Corrections** tab: every change to a week that had been exported or paid, with its adjustment, the period it was carried to and its status (Scheduled, Exported in EXP-xxxx, Paid) and the reason
5. The payroll flag never grants access to other people's timesheet details, notes, or analytics — only approved hours. (A payroll user still has their own employee pages, and manager rights for their own tree if they manage people — D-12.)
6. Because the payroll database is a separate file, it can be backed up, handed over, or moved to a different server later without the rest of the app.

## B.5 Timesheet status flow

| From | Event | To |
|---|---|---|
| (none) | Employee saves the week | **DRAFT** |
| DRAFT | Employee submits before Saturday 12:00 | **SUBMITTED** |
| DRAFT or (none) | Saturday 12:00 passes without submitting | **LOCKED** (missed) |
| SUBMITTED (both weeks) | Manager approves the period | **APPROVED** → payroll record written. DRAFT / LOCKED / REOPENED weeks block approval (D-06) |
| SUBMITTED | Manager rejects the period | **REOPENED** (`reopen_until` per D-21; D-07) |
| LOCKED | Manager clicks **Unlock** on the approval page | **REOPENED** (window per D-21); creates a manager-authored ChangeRequest + audit entry (D-06) |
| LOCKED / SUBMITTED / APPROVED | Change request → manager unlocks | **REOPENED** (window per D-21); payroll record superseded if it existed |
| LOCKED / SUBMITTED / APPROVED | Change request → manager edits directly | **SUBMITTED** (approval reset to PENDING; payroll record superseded) |
| REOPENED | Employee resubmits | **SUBMITTED** (`is_late` stays True if past the original deadline, D-08) |
| REOPENED | `reopen_until` passes without resubmission | **LOCKED** (D-08, D-21) |

**Week and deadline (D-111, D-112):** a week runs Sunday → Saturday, so the Saturday 12:00 deadline falls on its last day; Saturday afternoon may be entered in advance (D-09).

**Reopen window (D-21):** `reopen_until` = the later of (unlock/reject time + 48 hours) and the week's normal Saturday 12:00 deadline. A week unlocked on Wednesday therefore stays editable until Saturday 12:00.

**Who may change APPROVED (D-10):** `PeriodApproval` is the source of truth. Only `timesheets/services/approvals.py` may move a `Timesheet.status` to or from APPROVED, in the same database transaction as the matching `PeriodApproval` change.

**Payroll record status (D-15):** `CURRENT` → `EXPORTED` → `PAID`, forward only; any of these → `SUPERSEDED` when the week changes. Only `status`, `export_batch`, `exported_at`, `paid_at` and `superseded_at` may ever change. **Since Change 4:** a corrected version of a week that was already exported is created CURRENT and immediately becomes **SETTLED** (never exported; → SUPERSEDED if corrected again); its difference is a **PayrollAdjustment** (CURRENT → EXPORTED → PAID, D-118–D-120).

## B.6 Data model

Django "apps": `directory` (employees, teams, users), `timesheets` (projects, weeks, entries, approvals, change requests), `audit` (audit log), `payroll` (**payroll database**), `analytics` (calculations only, no tables).

### Main database (`db.sqlite3`)
```python
# directory/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    department = models.CharField(max_length=100)

class Employee(models.Model):              # the company employee directory
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"; INACTIVE = "INACTIVE"
    employee_code = models.CharField(max_length=20, unique=True)    # Employee ID, e.g. EMP-0004
    email = models.EmailField(unique=True)                          # stored lower-case; source of truth (D-20)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    job_title = models.CharField(max_length=100)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    manager = models.ForeignKey("self", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="reports")
    location = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)                    # set on deactivation (D-19)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    expected_weekly_minutes = models.PositiveIntegerField(default=2400)   # 40 h
    is_admin = models.BooleanField(default=False)
    is_payroll = models.BooleanField(default=False)                       # NEW
    # save() calls directory/services/accounts.py → sync_account(self), which updates the linked
    # User: is_staff/is_superuser = is_admin, is_active = (status == ACTIVE) (D-13), and
    # email = self.email lower-cased (D-20).

class User(AbstractUser):                  # login account — MUST exist before the first migrate
    username = None
    email = models.EmailField(unique=True)                          # always mirrors employee.email (D-20)
    employee = models.OneToOneField(Employee, on_delete=models.PROTECT, related_name="account")
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    must_change_password = models.BooleanField(default=False)       # set by an HR reset (D-91), migration 0002
    objects = UserManager()                # custom manager, email login (D-02) — directory/managers.py
    # The inherited "password" field stores only the Argon2 hash, e.g. "argon2$argon2id$v=19$..."
```

**User manager (D-02).** `UserManager.create_user(email, password, employee)` and `create_superuser(...)` both require an `employee`; flags and email are taken from it (D-13, D-20). `manage.py createsuperuser` asks for an **employee_code** that must exist, be ACTIVE, and have no account yet. Normal accounts come only from `seed_demo` or sign-up.

```python
# timesheets/models.py
class Project(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    active = models.BooleanField(default=True)

class Timesheet(models.Model):             # one per employee per week
    class Status(models.TextChoices):
        DRAFT="DRAFT"; SUBMITTED="SUBMITTED"; LOCKED="LOCKED"; REOPENED="REOPENED"; APPROVED="APPROVED"
    employee = models.ForeignKey("directory.Employee", on_delete=models.PROTECT, related_name="timesheets")
    week_start = models.DateField()        # always a Sunday (D-111)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    # to/from APPROVED only via timesheets/services/approvals.py (D-10)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_late = models.BooleanField(default=False)
    reopen_until = models.DateTimeField(null=True, blank=True)
    manager_note = models.TextField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["employee", "week_start"], name="one_sheet_per_week")]

class TimeEntry(models.Model):            # one row = one entry; no row limit (D-35)
    class Category(models.TextChoices):
        PROJECT="PROJECT","Project work"; MEETING="MEETING","Meetings"; TRAINING="TRAINING","Training"
        OTHER="OTHER","Other"; BREAK="BREAK","Break time"          # Break: unpaid (D-39)
        PTO="PTO","PTO"; SICK="SICK","Sick"; HOLIDAY="HOLIDAY","Holiday"
    WORK = {PROJECT, MEETING, TRAINING, OTHER}; TIMED = WORK | {BREAK}; LEAVE = {PTO, SICK, HOLIDAY}
    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE, related_name="entries")
    work_date = models.DateField()         # within the week and within hire_date…end_date (D-19)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.PROTECT)
    # PROJECT entries must have an active project; all other categories (Break too) none (D-18, D-39)
    category = models.CharField(max_length=10, choices=Category.choices)
    start_time = models.TimeField(null=True, blank=True)   # work and Break rows only (D-37)
    end_time = models.TimeField(null=True, blank=True)     # after start, same day; leave has none (D-40)
    minutes = models.PositiveIntegerField()    # end − start, or leave hours; 15-min steps; day ≤ 1440 (D-42)
    reason = models.CharField(max_length=255, blank=True)  # optional (D-128); was "notes" before Phase 5b
    class Meta:
        constraints = [  # both times or neither; end after start
            models.CheckConstraint(condition=Q(start_time__isnull=True, end_time__isnull=True)
                                   | Q(start_time__isnull=False, end_time__isnull=False), name="entry_times_paired"),
            models.CheckConstraint(condition=Q(start_time__isnull=True) | Q(end_time__gt=F("start_time")),
                                   name="entry_end_after_start")]

class PeriodApproval(models.Model):        # one per employee per 2-week period
    class Status(models.TextChoices):
        PENDING="PENDING"; APPROVED="APPROVED"; REJECTED="REJECTED"
    employee = models.ForeignKey("directory.Employee", on_delete=models.PROTECT)
    period_start = models.DateField()      # Sunday of week 1 (D-113)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    approver = models.ForeignKey("directory.Employee", null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="approvals_made")
    decided_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)

class ChangeRequest(models.Model):
    class Status(models.TextChoices):
        OPEN="OPEN"; REJECTED="REJECTED"; UNLOCKED="UNLOCKED"; EDITED="EDITED"
    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE, related_name="change_requests")
    requester = models.ForeignKey("directory.Employee", on_delete=models.PROTECT)
    # requester is the manager for an Unlock from the approval page (D-06)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    reviewer = models.ForeignKey("directory.Employee", null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="requests_reviewed")
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
```

```python
# audit/models.py
class AuditLog(models.Model):
    class Action(models.TextChoices):     # full list (D-22)
        CREATE="CREATE"; UPDATE="UPDATE"; DELETE="DELETE"; SUBMIT="SUBMIT"; APPROVE="APPROVE"
        REJECT="REJECT"; UNLOCK="UNLOCK"; PUBLISH="PUBLISH"; SUPERSEDE="SUPERSEDE"
        EXPORT="EXPORT"; PAY="PAY"; SYNC="SYNC"
    actor = models.ForeignKey("directory.Employee", null=True, blank=True, on_delete=models.PROTECT)
    system_actor = models.CharField(max_length=40, blank=True)   # e.g. "seed_demo", "sync_payroll" (D-14)
    entity_type = models.CharField(max_length=40)
    entity_id = models.CharField(max_length=40)
    action = models.CharField(max_length=20, choices=Action.choices)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    change_request = models.ForeignKey("timesheets.ChangeRequest", null=True, blank=True,
                                       on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.CheckConstraint(       # exactly one of actor / system_actor (D-14)
            condition=(Q(actor__isnull=False) & Q(system_actor=""))
                    | (Q(actor__isnull=True) & ~Q(system_actor="")),
            name="audit_exactly_one_actor")]
```

### Payroll database (`payroll.sqlite3`) — NEW
```python
# payroll/models.py   (stored ONLY in the "payroll" database via payroll/routers.py)
class PayrollWeek(models.Model):
    class Status(models.TextChoices):
        CURRENT="CURRENT"; EXPORTED="EXPORTED"; PAID="PAID"; SETTLED="SETTLED"; SUPERSEDED="SUPERSEDED"
    # Snapshot fields — plain values, NOT foreign keys (Django can't link across databases)
    employee_code = models.CharField(max_length=20, db_index=True)
    employee_name = models.CharField(max_length=130)
    department = models.CharField(max_length=100)
    team = models.CharField(max_length=100, blank=True)
    week_start = models.DateField(db_index=True)
    period_start = models.DateField(db_index=True)
    regular_minutes = models.PositiveIntegerField()
    overtime_minutes = models.PositiveIntegerField()
    pto_minutes = models.PositiveIntegerField()
    sick_minutes = models.PositiveIntegerField()
    holiday_minutes = models.PositiveIntegerField()
    total_minutes = models.PositiveIntegerField()
    expected_weekly_minutes = models.PositiveIntegerField()
    approved_by_code = models.CharField(max_length=20)
    approved_by_name = models.CharField(max_length=130)
    approved_at = models.DateTimeField()
    source_timesheet_id = models.PositiveIntegerField()   # id in the main database
    version = models.PositiveIntegerField(default=1)
    # Everything above is frozen after creation. Only the fields below may change, forward only (D-15).
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CURRENT)
    export_batch = models.CharField(max_length=40, blank=True)
    exported_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)     # CURRENT → SETTLED (D-118)
    superseded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["employee_code", "week_start", "version"],
                                               name="one_version_per_week"),
                       models.UniqueConstraint(fields=["employee_code", "week_start"],      # D-66
                                               condition=~Q(status="SUPERSEDED"),
                                               name="one_live_record_per_week")]
    # save() refuses changes to frozen fields and backwards moves; delete(), QuerySet.update()
    # and QuerySet.delete() always raise AppendOnlyError (D-15, D-67).

class PayrollAdjustment(AppendOnlyRecord):   # Change 4 (D-119–D-121), payroll database only
    # frozen: employee_code/name, department, team, week_start (the corrected week),
    # week_period_start, period_start (carried to), old_version, new_version,
    # regular/overtime/pto/sick/holiday/total_minutes (signed IntegerFields), approved_by_code,
    # approved_by_name, approved_at, reason, source_timesheet_id, created_at
    status = ...   # CURRENT → EXPORTED → PAID, forward only; plus export_batch, exported_at, paid_at
    # UniqueConstraint(employee_code, week_start, new_version) "one_adjustment_per_version"
```

How the two databases work together:
- `settings.DATABASES` has `default` → `db.sqlite3` and `payroll` → `payroll.sqlite3`.
- `payroll/routers.py` sends every read, write and migration of the `payroll` app to the `payroll` database, and keeps all other apps out of it.
- Migrate both: `uv run python manage.py migrate` and `uv run python manage.py migrate --database=payroll`.
- `payroll/services/publish.py → publish_period(approval)` runs after an approval and writes the week records. It is **idempotent** (running it twice never creates duplicates), so `manage.py sync_payroll` can safely re-check all approved periods and fill in anything missing — this protects against the two databases getting out of step.

Design notes:
- The custom `User` model and its `UserManager` must be set up (`AUTH_USER_MODEL = "directory.User"`) **before the very first migrate** (D-02).
- Every app keeps business rules in a **services package**: `<app>/services/<module>.py` — never a single `services.py` (D-04).
- Work dates are `DateField`; moments in time are stored in UTC and shown in company time.
- Time is stored as whole **minutes** to avoid rounding errors; shown as hours (e.g. 37.75).

## B.7 Demo data (bigger, realistic, repeatable)

`seed_demo` builds a realistic company so every page has data from day one. It always produces the **same** data (fixed random seed), so tests and screenshots are repeatable.

### What gets created

| Item | Amount |
|---|---|
| Employees in directory | **~50** across 6 departments and 9 teams, 4 management levels |
| Fixed "core" employees | **13** (listed below — use these for testing) |
| Generated employees | ~37 (Faker, fixed seed), placed under the core managers |
| Login accounts already created | **All active employees except 3** sign-up test people (password = `DEMO_PASSWORD` from `.env`, stored as Argon2 hashes) |
| Projects | 8 (one inactive) |
| Timesheet history | **12 weeks** (period-aligned, D-27) for every employee with an account: mostly on time, some late, a few missed, one rejected period, one open change request. Work rows have realistic start/end times (first start 08:00–09:30), a reason, and a 30–60 min **lunch Break**; leave days are hours only, holidays named ("Public holiday: Labor Day") (D-44) |
| Approved periods | All completed periods whose two weeks are both SUBMITTED are approved, except the most recent period (left **pending** to test approvals). Periods containing a missed (LOCKED) week stay **pending** (D-06) |
| Payroll database | Pre-filled with every approved week, after the main data commits: the oldest approved periods EXPORTED and PAID (one batch per period, by payroll@), the next one EXPORTED, the newest CURRENT, plus one SUPERSEDED correction (v1 one hour short, v2 CURRENT) (D-73) |
| Audit log | Entries for the seeded approvals, rejection and manager edit. Rows the seed itself creates use `system_actor="seed_demo"`; seeded human decisions name the manager as `actor` (D-14) |

### Core employees (`data/employees_core.csv`)
```csv
employee_code,email,first_name,last_name,job_title,team,department,manager_code,location,hire_date,is_admin,is_payroll,status
EMP-0001,ceo@yourcompany.com,Asha,Rao,CEO,Leadership,Executive,,Dallas,2018-01-08,true,false,ACTIVE
EMP-0002,eng.director@yourcompany.com,Mark,Lee,Engineering Director,Engineering,Technology,EMP-0001,Dallas,2019-03-11,false,false,ACTIVE
EMP-0003,eng.manager@yourcompany.com,Priya,Shah,Engineering Manager,Platform,Technology,EMP-0002,Frisco,2020-06-01,false,false,ACTIVE
EMP-0004,dev1@yourcompany.com,John,Kim,Software Engineer,Platform,Technology,EMP-0003,Frisco,2022-02-14,false,false,ACTIVE
EMP-0005,dev2@yourcompany.com,Sara,Ng,Software Engineer,Platform,Technology,EMP-0003,Remote,2023-09-05,false,false,ACTIVE
EMP-0006,qa1@yourcompany.com,Ravi,Kumar,QA Engineer,Platform,Technology,EMP-0003,Frisco,2024-01-22,false,false,ACTIVE
EMP-0007,hr@yourcompany.com,Lena,Ortiz,HR Manager,People,HR,EMP-0001,Dallas,2019-10-01,true,false,ACTIVE
EMP-0008,ops.manager@yourcompany.com,Tom,Hall,Operations Manager,Operations,Ops,EMP-0001,Dallas,2020-04-15,false,false,ACTIVE
EMP-0009,ops1@yourcompany.com,Mei,Chen,Operations Analyst,Operations,Ops,EMP-0008,Dallas,2023-03-01,false,false,ACTIVE
EMP-0010,ops2@yourcompany.com,Ali,Hassan,Operations Analyst,Operations,Ops,EMP-0008,Remote,2025-07-07,false,false,ACTIVE
EMP-0011,payroll@yourcompany.com,Nina,Patel,Payroll Specialist,Payroll,Finance,EMP-0012,Dallas,2021-05-17,false,true,ACTIVE
EMP-0012,finance.manager@yourcompany.com,Omar,Diaz,Finance Manager,Payroll,Finance,EMP-0001,Dallas,2019-08-19,false,true,ACTIVE
EMP-0013,former@yourcompany.com,Leo,Grant,Software Engineer,Platform,Technology,EMP-0003,Frisco,2021-01-11,false,false,INACTIVE
```

### Ready-made logins for testing

| Login email | Role(s) to test |
|---|---|
| `hr@yourcompany.com` | Admin (Django Admin, everything) |
| `ceo@yourcompany.com` | Admin + top-level manager (whole company tree) |
| `eng.director@yourcompany.com` | Manager of managers (indirect reports) |
| `eng.manager@yourcompany.com` | Manager (approvals, change requests) |
| `dev1@yourcompany.com`, `dev2@yourcompany.com` | Employee |
| `ops.manager@yourcompany.com` | Manager of a second team |
| `payroll@yourcompany.com` | **Payroll** (payroll database, export) |
| `finance.manager@yourcompany.com` | Payroll + manager |

All use the password in `DEMO_PASSWORD`.

### Left without accounts — for testing sign-up

| Email | Expected sign-up result |
|---|---|
| `qa1@yourcompany.com`, `ops1@yourcompany.com`, `ops2@yourcompany.com` | ✅ Allowed (in directory, active, no account) |
| `former@yourcompany.com` | ❌ Refused (INACTIVE) |
| `nobody@yourcompany.com` | ❌ Refused (not in directory) |
| `dev1@gmail.com` | ❌ Refused (wrong domain) |
| `dev1@yourcompany.com` | ❌ "Account already exists" |

### Commands
```bash
uv run python manage.py seed_demo            # build the demo company (refuses if data already exists)
uv run python manage.py seed_demo --large    # ~500 employees, 52 weeks — performance testing
uv run python manage.py sync_payroll         # re-check approved periods → payroll database
uv run python manage.py import_employees data/your_file.csv   # load a real directory later
```

## B.8 Pages

| URL | Who | Purpose |
|---|---|---|
| `/login/`, `/signup/`, `/logout/` | Public | Authentication |
| `/` | All | Dashboard: personal analytics + current-week card + countdown |
| `/profile/` | All | Directory details; change password |
| `/timesheets/` | All | My weeks and their status |
| `/timesheets/<YYYY-MM-DD>/` | All | Week entry rows and day summary; Save draft / Submit / Request change |
| `/requests/` | All | My change requests |
| `/team/` | Managers | Hierarchy analytics + this week's compliance |
| `/team/<employee_code>/` | Managers (own tree) | Read-only drill-down |
| `/approvals/` | Managers | Biweekly approval list by period |
| `/approvals/<period_start>/<employee_code>/` | Managers | Review both weeks; approve or reject; unlock a LOCKED week (D-06) |
| `/approvals/bulk/` | Managers, admins | POST: approve the ticked clean rows of a period (D-63) |
| `/approvals/requests/` | Managers | Change-request inbox |
| `/approvals/requests/<id>/` | Handler (D-47) | Request detail: Reject / Unlock, optional note |
| `/approvals/requests/<id>/edit/` | Handler (D-47) | Edit directly: the employee's rows, same rules as Phase 5b |
| `/payroll/` | **Payroll, Admin** | Approved hours by period; filters; totals; Export CSV; Mark paid |
| `/payroll/corrections/` | **Payroll, Admin** | Weeks changed after export/payment |
| `/admin/` | Admins | Django Admin |

Every view checks permissions on the server — hiding a menu item is never the only protection.

## B.9 Core business logic (plain Python functions)

Every app uses a services package, `<app>/services/<module>.py` (D-04).

| # | Function | Location |
|---|---|---|
| 1 | `week_start_for(d)` → Sunday of that Sunday→Saturday week (D-111); `week_days` Sun…Sat; `working_days` Mon–Fri (D-114) | `timesheets/services/calendar.py` |
| 2 | `deadline_for(week_start, tz)` → Saturday 12:00 company time, the week's last day (D-112) | same |
| 3 | `effective_status(timesheet, now)` → DRAFT becomes LOCKED after deadline; REOPENED becomes LOCKED after `reopen_until` (D-08, D-21) | same |
| 4 | `pay_period_for(d, anchor)` → `(period_start, week1, week2)`; 14 days from a Sunday anchor, `ValueError` for any other day (D-113) | same |
| 5 | `expected_minutes_for(employee, week_start)` → `expected_weekly_minutes × active weekdays (Mon–Fri, within hire_date…end_date) / 5`; 0 for weeks fully outside employment (D-19) | same |
| 6 | `reporting_tree(employee)` → all reports, cycle-safe; built in memory from one `(id, manager_id)` query (D-86); `team_scope(viewer, scope)` → whole tree (everyone for admins) or direct reports, never the viewer (D-81) | `directory/services/permissions.py` |
| 7 | `can_view`, `can_approve`, `can_edit`, `can_access_payroll` — `can_approve` = direct manager, or Admin for employees with no manager, never self (D-11); payroll flag grants nothing beyond `/payroll/` (D-12) | same |
| 8 | `sync_account(employee)` → copies is_admin → is_staff/is_superuser, status → is_active, email (lower-cased) → User (D-13, D-20) | `directory/services/accounts.py` |
| 9 | `validate_entries(...)` → reason optional, ≤ 255 (D-36, D-128); work and Break rows: start/end in 15-min steps, end after start, same day (D-37), no overlaps (D-38); leave: hours only (D-40); dates in week and within hire_date…end_date (D-19); PROJECT ⇔ active project, Break never a project (D-18, D-39); work + Break + leave ≤ 24 h/day (D-42) | `timesheets/services/validation.py` |
| 10 | `approve_period`, `reject_period`, `reset_approval`, `unlock_week` — the **only** code that moves a week to/from APPROVED, in one transaction with PeriodApproval (D-06, D-07, D-10); `unlock_week` and `reject_period` set `reopen_until` per D-21 | `timesheets/services/approvals.py` |
| 11 | `check_signup_eligibility(email)` | `directory/services/signup.py` |
| 12 | `split_hours(entries, expected)` → regular / overtime / PTO / sick / holiday; Break time is excluded from regular hours and overtime (D-45) | `payroll/services/hours.py` |
| 13 | `publish_period(approval, …)` (idempotent, D-66; settles corrected versions of once-exported weeks and creates their adjustments, D-118–D-121), `supersede_week(...)`; run after the main commit by the timesheet hooks (D-65); `sync_payroll(at)` (also creates missing adjustments, D-125) | `payroll/services/publish.py`, `payroll/services/adjustments.py`, `payroll/services/sync.py` |
| 14 | `export_period(...)` (whole period: CURRENT weeks + CURRENT adjustments, batch `EXP-0001`…, D-68, D-123), `batch_csv(...)` (WEEK and ADJUSTMENT rows; text cells spreadsheet-safe), `mark_paid(...)` (per batch, both kinds, D-69), `corrections()` (with adjustments, D-124), `carry_period(...)` (D-121) | `payroll/services/export.py`, `payroll/services/adjustments.py` |
| 17 | `approval_deadline_for(period_start)` → `APPROVAL_DEADLINE_DAYS` after the period's last day at `APPROVAL_DEADLINE_TIME`, company time (default Monday 12:00, D-133); `must_be_approved(employees, period_start)` → the one "who must be approved" rule, used per manager by `period_rows` and company-wide by `company_period_rows` (D-54, D-134) | `timesheets/services/calendar.py`, `timesheets/services/approvals.py` |
| 18 | `period_state(period_start, now)` → OPEN / READY (live) or FINALIZED / PAID (saved), approved x of y, why it isn't ready (D-132, D-133); `period_items` + `build_lines` → the register's lines from the PayrollWeek and PayrollAdjustment records only — the same code for the preview and for finalizing (D-134, D-136); `finalize(...)` (one batch, frozen lines, audit, D-135); `mark_paid(...)`; `register_csv(...)`; `build_registers(...)` for earlier exports (D-137); `closed_periods()` / `carry_period(...)` (D-136) | `payroll/services/register.py`, `payroll/services/adjustments.py` |
| 15 | Dashboard and team metrics (on-time rate, overtime, hours by project, missed weeks): `dashboard_for`, `punctuality`, `overtime`, `hours_by_project`, `hours_by_category`, `approval_outcomes` — built on `week_state`, `summarize` and `split_hours` (D-74–D-79) | `analytics/services/metrics.py` |
| 16 | `summarize(entries, employee, week_start)` → per day and week: Hours worked (work rows only), Break, Leave, expected, first start, last end (D-41) | `timesheets/services/summary.py` |

## B.10 Quality rules

- **Passwords:** Argon2 hashing (`PASSWORD_HASHERS` with `Argon2PasswordHasher` first); minimum 12 characters; plain passwords never logged, emailed, shown, or stored; admins can only reset.
- **Security:** CSRF protection, secure sessions, lockout via django-axes; every query permission-checked on the server; `.env`, `db.sqlite3` and `payroll.sqlite3` never committed; `DEBUG=False` in production mode.
- **Payroll integrity:** payroll records are append-only as defined in D-15 (snapshot and hours fields frozen; lifecycle fields move forward only; corrections by superseding); every publish, supersede, export (register finalize), payment and sync writes an AuditLog row (PUBLISH / SUPERSEDE / EXPORT / PAY / SYNC, D-22).
- **Privacy:** managers see only their tree; payroll sees only approved hours.
- **Usability:** Chrome and Safari, desktop and tablet; keyboard-friendly grid.
- **Performance:** each page under 1 second with the `--large` seed.
- **Reliability:** one-command backup of **both** databases; migrations committed to Git.

## B.11 Testing strategy (NEW)

### Layers of testing

| Layer | What it checks | Tools | Speed |
|---|---|---|---|
| **Unit tests** | Single functions: deadline maths, hour splitting, permissions, sign-up rules | pytest, time-machine | Milliseconds each |
| **Integration tests** | Views + database together: submit a week, approve a period, payroll record appears | pytest-django, Django test client, factory_boy | Fast |
| **End-to-end (E2E) tests** | A real browser clicks through the app like a user | Playwright for Python | Slower (run before committing) |
| **Manual acceptance tests** | You click through the checklist in D.1 | Your browser + demo logins | — |

### Test databases are separate
`pytest` automatically creates **temporary test databases** (for both `default` and `payroll`) and deletes them afterwards. Running tests **never touches** your real `db.sqlite3` or `payroll.sqlite3`. Tests that use the payroll database declare `@pytest.mark.django_db(databases=["default", "payroll"])`.

### Folder layout
```
tests/
  conftest.py              # shared fixtures: company, users, logged-in clients, fixed clock
  factories.py             # factory_boy factories: Employee, User, Timesheet, TimeEntry, ...
  unit/
    test_calendar.py       # weeks, deadlines, pay periods, daylight saving
    test_permissions.py
    test_signup.py
    test_passwords.py
    test_accounts.py       # UserManager, createsuperuser, directory → account sync (D-02, D-13, D-20)
    test_audit.py          # exactly one of actor / system_actor (D-14)
    test_validation.py
    test_payroll_split.py
    test_metrics.py        # dashboard helpers (range, rate, totals)
    test_team_metrics.py   # team helpers (utilization, sorting, one-query tree)
    test_directory_rules.py # reporting loops, company email domain (D-89)
  integration/
    test_auth_views.py
    test_timesheet_flow.py
    test_row_actions.py    # change / delete a whole grid row: delete, merge, kinds, refusals, audit, markup (T-191–T-197, T-199)
    test_entry_form.py     # the grid on the week page and Edit directly: blank/partial entries, re-render, cell hours (T-89–T-91)
    test_grid.py           # weekly grid: layout, totals, add row, slots, leave, errors on cells, read-only (T-160–T-166), several slots per cell (T-184–T-186), optional reasons (T-188)
    test_sunday_week.py    # Sunday-to-Saturday weeks: last-day deadline, redirects, daylight-saving week (T-169, T-171, T-172)
    test_change_requests.py
    test_approvals.py
    test_payroll_publish.py
    test_payroll_pages.py  # /payroll/, export CSV, corrections, 403s (T-37–T-39, T-110, T-111)
    test_payroll_register.py # pay period registers: deadline, who, READY, lines, finalize, carry-forward, CSV, pages, backfill, sync (T-203–T-215)
    test_adjustments.py    # automatic pay adjustments: settle, carry forward, CSV, sync, append-only, settled label (T-173–T-182)
    test_analytics.py
    test_team.py           # /team/, drill-down, week view, large-data query count (T-123–T-132)
    test_admin.py
    test_admin_edit.py     # audited edits, read-only/no delete, deactivate, password reset, 403s (T-133–T-141, T-144, T-145)
    test_hardening.py      # DEBUG off: static files, friendly 404/500 (T-156)
    test_ui_theme.py       # theme stylesheet, one status badge component, WCAG AA contrast (T-157–T-159)
    test_admin_csv.py      # employee CSV import preview/confirm and export round-trip (T-142, T-143)
    test_import_employees.py
    test_layout.py         # menus, header, placeholder pages, profile (FR-4, D-30)
    test_seed_demo.py
  e2e/
    conftest.py            # live test server, fixed clock, a small company, one browser context per person (D-94)
    test_e2e_flows.py      # marked @pytest.mark.e2e (T-146–T-155, T-167, T-183)
```

### Test case catalogue (must all exist and pass)

New catalogued tests continue as **T-43, T-44, …** and are added to this table in the same phase that writes them (D-16). Every catalogued test's docstring starts with its ID, e.g. `"""T-13: week still open at Saturday 11:59:59."""`; small helper tests don't need an ID (D-17).

| ID | Area | Test case | Expected |
|---|---|---|---|
| T-01 | Sign-up | Email with wrong domain | Refused |
| T-02 | Sign-up | Email not in directory | Refused with "Contact HR" |
| T-03 | Sign-up | Inactive employee | Refused |
| T-04 | Sign-up | Employee already has account | "Already exists" |
| T-05 | Sign-up | Valid directory email, mixed case + spaces | Account created; email stored lower-case |
| T-06 | Password | Stored password value | Starts with `argon2`, is **not** the typed password |
| T-07 | Password | Same password for two users | Different stored hashes (random salt) |
| T-08 | Password | Password shorter than 12 / too common | Rejected |
| T-09 | Login | Correct password | Logged in |
| T-10 | Login | 5 wrong attempts | Locked 15 minutes |
| T-11 | Login | Inactive employee with an account | Cannot log in |
| T-12 | Calendar | `week_start_for` on every day of the week | Its Sunday (D-111; until Change 3: Monday) |
| T-13 | Calendar | Deadline at Saturday 11:59:59 | Still open |
| T-14 | Calendar | Deadline at Saturday 12:00:00 | Locked |
| T-15 | Calendar | Weeks around the daylight-saving changes (March and November; both now fall on a week's first day, Sunday) | Deadline still Saturday 12:00 local |
| T-16 | Calendar | `pay_period_for` across year boundary (Sunday anchor 2026-01-04) | Correct 2-week period starting on a Sunday |
| T-17 | Validation | Times or leave hours not in 15-minute steps | Rejected |
| T-18 | Validation | Day total (work + Break + leave) over 24 h | Rejected (D-42) |
| T-19 | Validation | Entry date outside the week / inactive project | Rejected |
| T-20 | Timesheet | Save draft then submit before deadline | SUBMITTED, not late |
| T-21 | Timesheet | Employee edits after submitting | Forbidden |
| T-22 | Timesheet | No submission by deadline | LOCKED, counted as missed |
| T-23 | Change request | Employee requests change | Visible to own manager only |
| T-24 | Change request | Manager unlocks | REOPENED until the later of +48 h and the week's Saturday 12:00 deadline (D-21); after that without resubmission → LOCKED |
| T-25 | Change request | Manager edits directly | AuditLog with before/after |
| T-26 | Permissions | Employee opens `/team/` or another person's page | 403 Forbidden |
| T-27 | Permissions | Director sees indirect reports; manager sees only own tree | Correct sets |
| T-28 | Permissions | Reporting tree with a cycle in data | No infinite loop |
| T-29 | Approvals | Approve when one week is still DRAFT or LOCKED | Blocked |
| T-30 | Approvals | Approve both weeks | APPROVED; audit entry |
| T-31 | Approvals | Reject without comment | Blocked; with comment → REOPENED with `reopen_until` per D-21 |
| T-32 | Approvals | Non-manager tries to approve | 403 |
| T-33 | Payroll | Approval publishes 2 week records | Correct regular/overtime/PTO/sick/holiday split |
| T-34 | Payroll | 45 h worked + 8 h PTO, 40 h expected | 40 regular, 5 overtime, 8 PTO |
| T-35 | Payroll | `publish_period` run twice | No duplicates |
| T-36 | Payroll | Approved week edited later | Old record SUPERSEDED; new version after re-approval |
| T-37 | Payroll | Export CSV | File contents correct; records EXPORTED with batch number *Since Change 8:* done by Finalize & export; the detailed CSV is named `payroll-detail_<start>_to_<end>_EXP-0001.csv`; a second finalize is refused; a person approved afterwards is carried to the next register (D-135, D-136). |
| T-38 | Payroll | Manager / employee opens `/payroll/` | 403 |
| T-39 | Payroll | Superseded week that was already exported | Listed in Corrections |
| T-40 | Analytics | On-time rate, overtime, hours by project for known data | Exact expected numbers |
| T-41 | Seed | `seed_demo` | ~50 employees, 3 sign-up candidates without accounts, payroll records exist |
| T-42 | Seed | `seed_demo` run twice | Second run refuses, data unchanged |
| T-43 | Change request | Week unlocked on Wednesday (D-21) | Still editable until Saturday 12:00; LOCKED after that if not resubmitted |
| T-44 | Accounts | `create_user` / `create_superuser` without an employee | Refused (D-02) |
| T-45 | Accounts | `create_user` for an employee (mixed-case email) | Email lower-cased from the directory; is_staff/is_superuser/is_active taken from the employee (D-02, D-13, D-20) |
| T-46 | Accounts | `createsuperuser` with an unknown, INACTIVE, non-admin or already-linked employee_code | Refused; no account created (D-02, D-23) |
| T-47 | Accounts | `createsuperuser` with an ACTIVE admin employee without an account | Superuser linked to the employee; email from the directory; Argon2 password (D-02) |
| T-48 | Accounts | Employee `is_admin` switched on, then off, and saved | User is_staff and is_superuser follow (D-13) |
| T-49 | Accounts | Employee set INACTIVE, then ACTIVE, and saved | User.is_active follows (D-13) |
| T-50 | Accounts | HR changes Employee.email (mixed case, spaces) | Employee and User email both updated, lower-cased (D-20) |
| T-51 | Accounts | Second employee given an existing email in different case | Refused; both emails stay unique (D-20) |
| T-52 | Audit | AuditLog with both `actor` and `system_actor`, or neither | Refused by `record()` and by the database constraint; exactly one → saved (D-14) |
| T-53 | Import | `import_employees` on a new CSV (manager listed after their report, optional `end_date` column) | Employees, teams, flags, status, end_date and manager links created; CREATE audit rows with system_actor |
| T-54 | Import | Same `employee_code`s imported again with changes | Updated in place, no duplicates; linked User synced (D-13, D-20); UPDATE audit with before/after |
| T-55 | Import | CSV with an unknown manager, bad status/date/boolean, duplicate code or email, missing column | Nothing imported; every error listed with its line |
| T-56 | Seed | Approvals created by `seed_demo` | Only periods with both weeks SUBMITTED are APPROVED; most recent completed period and periods with a LOCKED week stay PENDING; approver = direct manager (HR for the CEO), never self (D-06, D-11) |
| T-57 | Seed | Audit rows created by `seed_demo` | Seed's own rows use system_actor `seed_demo`; approvals, rejection, unlocks and the manager edit name the manager as actor (D-14) |
| T-58 | Login | Anonymous user opens `/`, `/admin/`, or any other page except `/login/` and `/signup/` | Redirected to `/login/?next=…`; login and sign-up pages open without a session (D-24) |
| T-59 | Databases | django-axes and every other non-payroll app after migrating both databases | Their tables exist only in the main database; payroll database holds only `django_migrations` (+ payroll tables from Phase 8) | *Change 4 adds `payroll_payrolladjustment` to the payroll database's tables.*
| T-60 | Permissions | `can_approve` for direct manager, higher manager, self | Only the direct manager; never self, never the director of an indirect report (D-11) |
| T-61 | Permissions | Admin approving with and without a manager on the employee | Admin approves only employees with no manager, never themselves; the CEO is approved by the HR admin, not by the CEO (D-11) |
| T-62 | Permissions | Payroll user (no reports) opens `/payroll/`, `/team/`, `/approvals/`, another person's page | Payroll 200; everything else 403; `can_view` others False (D-12) |
| T-63 | Permissions | Payroll user who is also a manager | Gets manager rights for their own tree (Team, Approvals, can_view/can_approve reports); nothing outside it (D-12) |
| T-64 | Layout | Menu for employee, manager, payroll user, admin | dev1: no Team/Approvals/Payroll/Admin; manager: Team + Approvals; payroll: Payroll; admin: Admin link; header shows name, Employee ID, job title, team (FR-4) |
| T-65 | Profile | `/profile/` | Shows the directory details read-only (FR-4); no editable directory fields |
| T-66 | Profile | Password change | Too short (<12) rejected; valid change keeps the user logged in, new password works, old does not; AuditLog row contains no password or hash |
| T-67 | Validation | PROJECT entry without a project; MEETING/PTO entry with a project | Both rejected; PROJECT with an active project and other categories without one accepted (D-18) |
| T-68 | Validation | Entry before `hire_date` or after `end_date` | Rejected; entries on employed days of the same week accepted (D-19) |
| T-69 | Calendar | `expected_minutes_for` for hire mid-week, end mid-week, part-timer, and a week fully outside employment | Prorated by active weekdays (e.g. 2400 × 3/5 = 1440); 0 outside employment (D-19) |
| T-70 | Timesheet | Unsubmitted past weeks before `hire_date` / after `end_date` vs partly employed weeks | Fully outside employment never missed; partly employed week missed if not submitted (D-19) |
| T-71 | Timesheet | Submit a week | AuditLog SUBMIT row with the employee as actor, after = status SUBMITTED, week_start, submitted_at, is_late, worked/break/leave minutes |
| T-72 | Validation | Work/Break row with end before or equal to start, or times not on 15-minute steps | Rejected (D-37) |
| T-73 | Validation | Overlapping timed rows on one day, including a Break inside a work row | Rejected; back-to-back rows (12:00–12:30, 12:30–13:00) accepted (D-38) |
| T-74 | Validation | Row with a reason over 255 characters | Rejected; 255 is fine (D-36). *Since D-128 an empty reason is accepted (T-187).* |
| T-75 | Validation | Break with a project, or Break without times | Rejected (D-39) |
| T-76 | Validation | PTO/Sick/Holiday with a start or end time; work row without times | Rejected (D-37, D-40) |
| T-77 | Timesheet | Day with work, a Break and leave | Hours worked counts only work rows; Break and Leave shown separately; first start/last end; per-day and week totals (D-41) |
| T-78 | Timesheet | Submit a week whose only rows are Breaks | Refused; nothing submitted (D-43) |
| T-79 | Timesheet | 20 entries on one day, plus entries on other days | All saved and shown (22 grid slots); no limit; the 24-hour rule still applies (D-35, D-42) |
| T-80 | Seed | `seed_demo` history | Every week passes `validate_entries`; every row has a reason; timed rows have times; lunch breaks and leave rows exist; Break never has a project (D-44) |
| T-81 | Change request | Request on DRAFT, NOT_STARTED, REOPENED or future week; second OPEN request on a week | Refused; first request on SUBMITTED/LOCKED/APPROVED (incl. a missed week with no timesheet) accepted (D-46) |
| T-82 | Change request | Who handles: employee with a manager, the CEO (no manager), an admin's own request | Direct manager only; HR admin for the CEO; nobody handles their own; others get 403 on detail and actions (D-47) |
| T-83 | Change request | Raise, reject, unlock, edit | Each writes one AuditLog row (CREATE / REJECT / UNLOCK / UPDATE) with the right actor, linked request and before/after (D-48–D-50) |
| T-84 | Change request | Edit directly with an overlap, a reason over 255 characters (a missing one before D-128), a Break with a project, a Break-only week, >24 h, no rows | Refused with the Phase 5b messages; nothing changed (D-49) |
| T-85 | Change request | Edit or unlock a week in an APPROVED period | PeriodApproval → PENDING, both weeks leave APPROVED, `supersede_payroll_week` called for each, in one transaction (D-10, D-53) |
| T-86 | Timesheet | Unlocked week from two weeks ago | Employee can open and save it until `reopen_until`; saves write an UPDATE audit with before/after; after the window → LOCKED (D-51) |
| T-87 | Timesheet | Late flag after reopening | Missed week unlocked and submitted later → is_late True; on-time week reopened and resubmitted after Saturday → stays on time (D-08, D-52) |
| T-88 | Layout | Open-request count in the menu | Handlers see "Change requests" with the count of open requests they may handle; employees without reports don't see it |
| T-89 | Timesheet | Week page and Edit directly (weekly grid since Change 2) with untouched or partial entries | The grid renders no blank slots; an entry with nothing typed is ignored; one with only hours or only a reason is refused ("choose a category") (D-35, D-107) |
| T-90 | Timesheet | Save with an error, then again, on the week page and Edit directly (grid) | The grid shows exactly the posted slots, and a row added without slots is kept; nothing extra is added on re-render (D-107) |
| T-91 | Timesheet | Cell hours on the week page and Edit directly (grid) | Each cell shows its hours with 2 decimals (08:30–12:00 → 3.50; Break 0.75; leave as typed, 1.50) on page load and after an error; the cell with the error is marked invalid (D-107, D-108) |
| T-92 | Approvals | Unlock a LOCKED week from the approval page (with and without an open employee request; missed week with no timesheet) | REOPENED per D-21; manager-authored UNLOCKED ChangeRequest or the open request resolved; UNLOCK audit (D-06, D-59) |
| T-93 | Approvals | Reject with a comment, employee resubmits | Comment shown on the employee's week page; after resubmission the period is PENDING again (audited) and approvable once both weeks are submitted (D-07, D-60) |
| T-94 | Approvals | Approve calls the payroll hook inside its transaction | Hook called once with the approval; if the hook itself fails, nothing changes (PeriodApproval, weeks, audit). A failure of the later payroll *write* does not undo the approval — see T-107 (D-10, D-61, D-65) |
| T-95 | Approvals | Who sees and approves which rows | Manager: direct reports only (not indirect, never self); HR admin: the CEO; CEO never sees own row; approving self or a non-direct report → 403 (D-11, D-54) |
| T-96 | Approvals | Bulk approve | Only clean rows have a checkbox; posted ineligible rows are skipped with a reason; each eligible employee approved in its own transaction; summary of approved and skipped (D-63) |
| T-97 | Approvals | Pay-period dates | 14-day periods from the Sunday anchor (D-113); default = most recent completed period; any date snaps to its period start; future periods refused; Previous/Next links (D-54) |
| T-98 | Approvals | Flags | Late, overtime (Hours worked above prorated expected; Break never counts) and missing days (employed weekday with no entries; leave counts) per D-55 |
| T-99 | Approvals | 403 cases | Non-manager on list, detail, bulk and POST actions; manager on someone not their direct report; admin on an employee who has a manager; anyone on themselves |
| T-100 | Approvals | Period with one week outside employment (hired in week 2, or left in week 1) | Approvable when the employed week is SUBMITTED; the other week shows "not employed" (D-56) |
| T-101 | Approvals | Open change request in the period | Approve/Reject blocked with the reason; row not bulk-eligible (D-58) |
| T-102 | Timesheet | Employee week page approval status | "Approved by … on …", the rejection comment, or "Waiting for approval by …" |
| T-103 | Payroll | Overtime rule: partial week (prorated expected), Break rows, PTO/Sick/Holiday, worked below expected | Regular = min(worked, expected), overtime = the rest; leave separate; Break never counted; hours shown with 2 decimals (D-64) |
| T-104 | Payroll | Change a frozen field; move status backwards; `update()` / `delete()` / `bulk_update()` | All refused with AppendOnlyError; forward moves work and set each lifecycle field once (D-15, D-67) |
| T-105 | Payroll | Deactivated employee's approved period | Published (prorated expected), exported and paid like anyone else's (D-19, D-71) |
| T-106 | Payroll | `publish_period` and `sync_payroll` run repeatedly | No duplicates; sync publishes missing periods and supersedes stale records; one SYNC audit row per run with system_actor `sync_payroll` (D-14, D-66) |
| T-107 | Payroll | Payroll write fails after the approval commits | Approval stays APPROVED; no partial payroll rows; error logged; out-of-sync banner; `sync_payroll` then publishes (D-65) |
| T-108 | Payroll | Main transaction rolls back after the hook | Nothing is written to payroll (D-65) |
| T-109 | Payroll | Supersede fails after an edit commits | Stale record remains until `sync_payroll` supersedes it; re-approval writes the next version; a live record from an older decision is superseded on publish (D-65, D-66) |
| T-110 | Payroll | CSV cells starting with `=`, `+`, `-`, `@` (or tab/CR) | Escaped with a leading `'`; other cells unchanged; batch numbers sequential (D-68) *Since Change 8:* through Finalize & export and the detailed CSV. |
| T-111 | Payroll | Who can open payroll pages | Payroll users and admins: 200; employee, manager, director: 403 on every payroll URL; a payroll user still gets 403 on others' timesheet details (D-12) *Since Change 8:* also the period page, register, detailed and all-periods CSVs, Finalize & export and Mark as paid; reasons never on the list or period page. |
| T-112 | Payroll | Mark as paid | EXPORTED → PAID for that batch only; CURRENT and later records untouched; PAY audit; repeating does nothing (D-69) |
| T-113 | Payroll | `backup_db` | Timestamped copies of both databases (same timestamp) that open with their tables (D-72) |
| T-114 | Seed | Payroll part of `seed_demo` | Every approved week has a live record; older periods EXPORTED/PAID with batches EXP-0001…; exactly one SUPERSEDED correction with its v2; EXPORT/PAY by payroll@ (D-73) *Since Change 8:* the older periods' registers are PAID and the next FINALIZED (EXP-0001…0004, finalized by payroll@ after the deadline), one line per person who had to be approved (0.00 for those not approved); the newest approved period is READY and its preview carries the +1.00 h adjustment (D-137). | *Since Change 4:* that correction's v2 is SETTLED (not re-exported) with one +1.00 h adjustment carried to the first unexported period (D-126).
| T-115 | Analytics | Range filter 4 / 12 / 26 weeks and an invalid value | Weeks end with the current week; counts change with the range; invalid → 12 (D-74) |
| T-116 | Analytics | On-time / late / missed edge cases: draft past deadline, no timesheet, late, reopened-and-resubmitted on-time week, missed week reopened and resubmitted, re-locked submitted week, missed week reopened but not resubmitted, current week | Classified per D-75 (first submission decides; never submitted = missed); current week not counted; the `/timesheets/` Missed badge agrees |
| T-117 | Analytics | New hire mid-range and a deactivated employee (end_date) | Weeks outside employment never shown, counted or missed; partial weeks prorated (D-19) |
| T-118 | Analytics | Overtime vs payroll | Dashboard overtime per approved week equals PayrollWeek.overtime_minutes; drafts excluded (D-76) |
| T-119 | Analytics | Own data only | `/` always shows the logged-in user's numbers; query parameters can't select another employee |
| T-120 | Analytics | Empty state (new hire, no timesheets) | Friendly messages instead of charts; page renders 200 (D-80) |
| T-121 | Analytics | Viewing the dashboard | No INSERT/UPDATE/DELETE; the same number of queries for 4 and 26 weeks (D-34, D-80) |
| T-122 | Analytics | Hours by category with Break and leave, approval outcomes, current-week card | Break shown apart and never in totals; outcomes per period with "in progress"; card shows the effective status and the server's deadline; chart data via `json_script` (D-77, D-78) |
| T-123 | Team | Team metrics for known data | Exact hours worked, utilization, on-time rate, late/missed, overtime and pending approvals per person; team hours and expected per week; hours by project; numbers on the page (D-82, D-84) |
| T-124 | Team | Utilization | Worked ÷ (expected − leave) over finished weeks; leave doesn't lower it; Break never counts; the current week is excluded; "—" when nothing is available; team average weighted by available hours (D-82) |
| T-125 | Team | Whole tree vs direct reports, team filter | Director: tree = manager + manager's reports; direct = manager only; team filter narrows; a bad team value = all teams; the viewer is never listed (D-81) |
| T-126 | Team | Access and 403s | Employee and payroll-only user → 403 on /team/, drill-down and week view; manager → 403 outside own tree, 404 for an unknown code; viewer can open own drill-down; payroll user who manages sees only their own tree (D-12, D-85) |
| T-127 | Team | Admin sees everyone | Admin's whole-tree list = every employee except themselves; direct = own direct reports only (empty state if none); admin can drill into anyone (D-81) |
| T-128 | Team | This week's compliance | Before Saturday 12:00 "Not submitted yet", after it "Missed"; people who submitted and people not employed this week are not listed (D-83) |
| T-129 | Team | Inactive employees | Shown only with a timesheet in the range, marked "inactive" (D-81) |
| T-130 | Team | Read-only drill-down and week view | Phase 9 parts for that person; no form, edit, submit, approve or "Open this week" controls; week view shows the rows read-only with status badges; non-Sunday redirects, future week 404 (D-85) |
| T-131 | Team | Viewing writes nothing | No INSERT/UPDATE/DELETE on the team page, drill-down and week view (D-34) |
| T-132 | Team | Fixed query count with large data | ~500 employees over 4 levels with 12 weeks of entries in the test DB: CEO (everyone), a director (125) and a manager (24) cost the same number of queries for 4 and 26 weeks (an admin one fewer: no "manages anyone?" check); `time_team_page` prints time, people, queries and 0 writes (D-86) |
| T-133 | Admin | Edit an employee in Admin (details, team, manager, expected hours, flags) | Saved; one UPDATE audit row, actor = the admin, before/after only for the changed fields; an unchanged save writes nothing; a failing audit write rolls back the edit (D-88) |
| T-134 | Admin | Add and edit a team and a project; add an employee | CREATE/UPDATE audit rows with the admin as actor; project code fixed after creation; employee code, status and end date not editable in the form; Import/Export/Reset password buttons shown (D-87, D-88) |
| T-135 | Admin | Read-only workflow records | Timesheet, ChangeRequest, PeriodApproval, AuditLog, PayrollWeek, User and axes AccessAttempt: add → 403, change POST → 403; Group is not registered (D-87) |
| T-136 | Admin | No delete anywhere | No registered model allows delete; delete URLs → 403 (GET and POST); "delete selected" never offered (D-87) |
| T-137 | Admin | Deactivate | Confirmation page with today as the default end date; INACTIVE + chosen end date, User inactive; their open session ends on the next request; timesheets kept; their SUBMITTED period can still be approved and published to payroll; audited (D-90, D-19) |
| T-138 | Admin | Deactivate and reactivate rules | Refused for yourself, someone still managing ACTIVE people, the last active admin, a future end date, a date before the hire date or the last entry — nothing changes; a manager together with all their reports is fine; reactivate → ACTIVE with end date cleared, audited; reactivating an active employee refused (D-90) |
| T-139 | Admin | Email and flag sync | Email change trimmed and lower-cased into Employee and User; other domain or an existing email (any case) refused; is_admin on/off → User is_staff/is_superuser follow (D-13, D-20, D-89) |
| T-140 | Admin | Directory safety rules | Removing your own admin flag, leaving no active admin, own manager, a manager loop and a new inactive manager are all refused with field errors; nothing saved (D-89) |
| T-141 | Admin | Password reset by HR | Weak password refused; Argon2 hash stored; audit row with no password or hash; the person's open session ends; axes lockout cleared; at next login every page leads to Profile until a new password is chosen, which clears the flag; own reset and no-account cases refused; `/admin/password_change/` → Profile (D-91) |
| T-142 | Admin | Employee CSV import in Admin | Errors listed with line numbers and nothing changes; a valid file shows a summary (created/updated with fields) and changes nothing until Confirm; a tampered confirmation is refused; Confirm imports with the admin as actor; a loop, self-demotion, self-deactivation, deactivating someone who still manages active people or an outside email in the file → nothing imported (D-89, D-92) |
| T-143 | Admin | Employee CSV export round-trip | Import columns + end_date; formula cells exported as `'=…` and read back unchanged; exporting then importing changes nothing; list filters apply; EXPORT audit row (D-92) |
| T-144 | Admin | Admin access 403s | Employee, manager, payroll-only and payroll+manager users → 403 on `/admin/`, model pages, import, export, reset password and actions; anonymous → `/login/`; a deactivated admin's session ends (D-93, D-29) |
| T-145 | Admin | Search and filters | Employees by name, manager, payroll flag, status, department; teams by name; timesheets by status; AuditLog by action, actor, entity type and date range (D-93) |
| T-146 | E2E | Sign-up in a real browser | Unknown email refused ("not in the company employee directory"); a directory employee without an account signs up and sees their name and code in the header |
| T-147 | E2E | Save a draft, then submit before Saturday 12:00 (fixed clock: Wed Oct 21 10:00) | PRJ-001 08:00–13:00 and a Break 13:00–14:00 on Monday; "+ Add row" for PRJ-001 again shows the "already has a row" notice; reopening the PRJ-001 cell lists its slot plus an empty, focused one, filled with 14:00–17:00 → the cell shows "8.00 · 2 slots", Total worked hours 8.00 (Break not counted); saved as Draft (3 entries); reopening shows both slots, reasons and the tooltip "08:00–13:00, 14:00–17:00"; Submit → Submitted and read-only, still "8.00 · 2 slots" (D-127) |
| T-148 | E2E | Week after the deadline (clock moved to Sat Oct 24 12:00) | The draft week shows Locked, with no inputs, Save draft or Submit |
| T-149 | E2E | Change request → manager Edit directly | Employee sends a request; manager edits Monday's end time and saves; the employee sees the week Submitted with 18:00; UPDATE audit row linked to the request, actor = manager |
| T-150 | E2E | Approve → payroll | Manager approves the period; the payroll user sees both week records (40.00 regular, 2.00 overtime on the long week) |
| T-151 | E2E | Reject with a comment → resubmit | Both weeks Reopened with the comment shown to the employee; after resubmitting both, the manager can approve again |
| T-152 | E2E | Payroll export and mark paid | Export CSV downloads a file with both records; records show Exported; Mark as paid → batch and records Paid *Since Change 8:* the register (Ready after the deadline) is finalized & exported in the in-page dialog, the detailed CSV downloaded with its period/batch file name, then marked paid. |
| T-153 | E2E | HR deactivates an employee | Admin action with today as the default end date; the employee's open browser is sent to login and logging in again fails with "Wrong email or password." |
| T-154 | E2E | HR password reset | Temporary password set in Admin; the employee logs in with it, is kept on Profile until they choose a new password, then pages open normally |
| T-155 | E2E | 403 pages | Employee (/team/, /approvals/, /payroll/, /admin/), payroll-only (/team/, /approvals/) and a manager outside a tree (/team/OPS1/) get the "Not allowed" page with status 403 |
| T-156 | Hardening | DEBUG off | Vendored static files still load; unknown URLs show the friendly 404 page and errors the plain 500 page, never a traceback or settings (D-96) |
| T-157 | UI | The theme stylesheet | Logged-in and login pages link `/static/css/theme.css` after the vendored Bootstrap; with DEBUG off it is served (200, `text/css`) and defines the `--ts-accent` token (D-100) |
| T-158 | UI | One status badge component | Every Timesheet, PeriodApproval, ChangeRequest and PayrollWeek status, plus Not started, Not employed, In progress and the Late/Missed/Overtime/Missing/Change requested/Read-only flags, has a tone with a CSS rule; no page template uses Bootstrap `text-bg-*` badges or the old `status_badge` filter; the week page renders `id="week-status">Submitted<` through the component (D-102) |
| T-159 | UI | Contrast | Every badge tone (text on its background), body and muted text, white on the accent and success buttons, the active menu item and error text reach at least 4.5:1, computed from the tokens in theme.css (D-100, WCAG AA) |
| T-160 | Grid | Layout and totals | A week with two projects, a meeting, a Break and PTO: one row per Project/Category in the set order (projects by code, then Meetings, Training, Other, Break (unpaid), leave); headers "Mon" / "Oct 19, 2026"; cell, row and footer totals with 2 decimals; the footer counts work only and equals the day summary's Hours worked; Break tagged "not counted", leave tagged "leave"; the day summary stays below (D-106) |
| T-161 | Grid | Add a row | The endpoint returns an empty row with 7 cells for a category or an active project; unknown category, missing or inactive project → 400; a row added without slots is kept through a failed save; bad keys ignored; never two rows for one key (D-107) |
| T-162 | Grid | Multi-slot cell | Two slots in one cell save as two entries; the cell shows the sum (8.50); its dialog shows both slots with times and reasons (D-107) |
| T-163 | Grid | Leave cell | Hours and a reason, no times (saved with no start/end); the cell shows 7.50 and the row is tagged leave; it is not in Total worked hours; the day summary shows it as Leave (D-40, D-106) |
| T-164 | Grid | Overlap error on the right cell | Overlapping slots in two rows on one day: nothing saved; both cells marked invalid with the unchanged overlap message inside their dialogs; the error summary links to the cell; other cells unmarked (D-38, D-108) |
| T-165 | Grid | Read-only grids | Submitted week, change-request detail, approval detail and Team week view: no inputs, selects or slot templates; each cell's dialog lists its slots' times, hours and reasons; no "+ Add row" (D-109) |
| T-166 | Grid | Existing week renders the same | An existing week with multi-slot cells, Break and leave: grid worked/Break/leave totals equal `summarize()`; one slot per entry; saving it unchanged keeps the entries identical and the day summary byte-identical (D-106, D-107) |
| T-167 | E2E | Weekly grid in a real browser | Add a row; adding it again gives no second row (D-127); a cell opens with Enter, two slots typed with live totals ("+ Add another time slot"), Esc closes and focus returns to the cell; leave not in the footer; leaving with unsaved changes asks first and saves nothing; Save draft saves; at 390 px the grid scrolls sideways with the first column fixed and the page doesn't (D-110) |
| T-168 | Calendar | Week boundaries | Saturday 2026-10-24 23:59:59 belongs to the week of Sun 18 Oct and is already locked/missed; Sunday 25 Oct 00:00 starts the next week (open, deadline Sat 31 Oct 12:00); `week_days` Sun…Sat; `working_days` Mon…Fri; expected hours 40 h, prorated for a Wednesday hire (D-111, D-114) |
| T-169 | Timesheet | Deadline on the last day | At Sat 24 Oct 11:59:59 a week with Monday work and a Saturday 13:00–15:00 entry entered in advance submits on time (D-09); at 12:00:00 another draft week is LOCKED and missed, saving refused (403) (D-112) |
| T-170 | Calendar | Pay-period anchor must be a Sunday | System check `timesheets.E001` for 2026-01-05 ("is a Monday; it must be a Sunday", hint with `PAY_PERIOD_ANCHOR=2026-01-04`); none for 2026-01-04; `pay_period_for` with a Monday anchor raises `ValueError`; 14-day periods both ways from the anchor start on Sundays (D-113) |
| T-171 | Timesheet | Redirect from a non-Sunday date | `/timesheets/2026-10-19/` (old Monday), Wednesday and Saturday → 302 to `/timesheets/2026-10-18/`; an old Monday of a past week → its Sunday; the Sunday opens; the Team week view redirects the same way (D-115) |
| T-172 | Calendar | Daylight-saving week | Week of Sun 1 Nov 2026 (clocks go back that night): Nov 1 and Sat Nov 7 belong to it; deadline Sat 7 Nov 12:00 CST = 18:00 UTC (the week before: 12:00 CDT = 17:00 UTC); a Sunday 09:00–17:00 entry saves as 8:00; expected 40 h; the draft locks at exactly 12:00 local (D-116) |
| T-173 | Payroll | Positive overtime adjustment after payment | A paid week corrected through Edit directly (+2 h) and re-approved: v2 SETTLED with no batch; one adjustment overtime +2.00, regular 0, total +2.00, versions 1→2, approver and approval time, reason = the change-request reason, carried to the next unexported period; the period's untouched week settles with no adjustment (D-118, D-119, D-121, D-122) |
| T-174 | Payroll | Negative adjustment | An exported, not yet paid week reduced by 1.5 h → adjustment regular −1.50, total −1.50; exported in the next batch as `-1.50` (a number, not escaped); shown as −1.50 on the Payroll page (D-119, D-123) *Since Change 8:* shown in the next register's carry-forward and exported by finalizing it. |
| T-175 | Payroll | No adjustment when the old version was never exported | Correction before export → v2 CURRENT, no adjustment; the next export has the v2 WEEK rows (D-119) |
| T-176 | Payroll | Several corrections of the same week | Paid v1 → v2 (+1 h) → v3 (−0.5 h against v2) while the first adjustment is still scheduled → adjustments +60 and −30 minutes, summing to v3 − v1; an unchanged re-approval creates nothing (D-119) |
| T-177 | Payroll | The new full version is never exported twice | After a correction the week's own period has nothing new to export; the next period's batch holds its WEEK rows plus one ADJUSTMENT row ("Export CSV (2 new week records, 1 adjustment)"); SETTLED records never get a batch; paid = v1 + difference = v2 (D-118, D-123) *Since Change 8:* the next register's preview shows only the +2.00 difference for the corrected week; its finalize exports the WEEK rows plus the ADJUSTMENT. |
| T-178 | Payroll | Carry-forward period | `carry_period`: the next period when unexported; skips periods that already have a batch; never earlier than the most recent completed period at re-approval; the next future period when everything is exported; moves on with time (D-121) |
| T-179 | Payroll | CSV, totals, Mark as paid, Corrections | CSV columns start `batch,employee_code,row_type`; ADJUSTMENT rows with blank `week_start`, `original_week` and version `1→2`; no reason in the CSV or on the Payroll page; totals show weeks 80.00 + adjustments +2.00 = 82.00; Corrections shows the period, the reason and Scheduled → Exported in EXP-0002 → Paid (EXP-0002); Mark as paid pays weeks and the adjustment; the untouched week shows "no adjustment (0.00)" (D-122–D-124) *Since Change 8:* on the register page (period 80.00 + carry +2.00 = 82.00), finalized and paid there; Corrections links to the register and shows its status. |
| T-180 | Payroll | sync_payroll creates missing adjustments idempotently | A pre-Change-4 state (v2 CURRENT after v1 was paid, no adjustment) → sync settles v2 and creates one adjustment (system actor `sync_payroll`, default reason); a second sync creates nothing; SYNC audit counts 1 then 0 (D-125) |
| T-181 | Payroll | Adjustments are append-only and audited | Frozen amounts, CURRENT→PAID skip, PAID→EXPORTED, delete, bulk update/delete and creating as EXPORTED all refused; a SETTLED week can't be exported; PUBLISH audit for the adjustment (actor = approver, versions, amounts, period, no reason); EXPORT and PAY rows count the adjustment (D-120, D-125) |
| T-182 | Payroll | Settled week shows where its difference was paid | Viewing the corrected week's own (old) period: the Settled week is labelled "Settled by adjustment in Sep 27 – Oct 10", linking to `?period=2026-09-27`, where the adjustment is listed; the period's untouched week shows "No difference to pay"; weeks that aren't Settled carry no label (D-124) *Since Change 8:* the link opens `/payroll/periods/2026-09-27/`; `?period=` links redirect there. |
| T-183 | E2E | "+ Add row" for a row that is already there | PRJ-001 added, then Meetings, then PRJ-001 again: the dialog closes with no error; a notice under the grid (`role="status"`) reads "PRJ-001 Customer Portal / Project work already has a row. Click a day to add another time slot (for example 2:00 PM – 5:00 PM)."; the PRJ-001 row is highlighted briefly and its Sunday cell focused; still one PRJ-001 row. PTO twice → "PTO already has a row. Click a day to enter or change its hours."; nothing saved (D-127) |
| T-184 | Grid | Two slots for one project on one day | PRJ-001 08:00–13:00 and 14:00–17:00 with a Break 13:00–14:00 on Sunday save as 3 entries in one PRJ-001 row and a Break row; the cell shows 8.00 with 2 slots in its dialog, the Break cell 1.00 "not counted"; footer, week total and day summary Hours worked 8:00, day summary Break 1:00 (D-38, D-41, D-127) |
| T-185 | Grid | An overlapping third slot is refused on the right cell | Adding 16:00–18:00 to the PRJ-001 Sunday cell of T-184: nothing saved (entries unchanged); the cell is marked invalid with "Sun 18 Oct: 14:00–17:00 PRJ-001 and 16:00–18:00 PRJ-001 overlap." in its dialog (3 slots kept) and in the error summary; the Break cell is not marked (D-38, D-108, D-127) |
| T-186 | Grid | Multi-slot hint | On the editable week, the submitted (read-only) week and the manager's Team week view a two-slot cell shows "8.00" + " · 2 slots", the title "08:00–13:00, 14:00–17:00" and the times in its accessible name; its dialog lists both slots; a single-slot cell has no title and no hint; the editable dialog offers "+ Add another time slot" (D-127) |
| T-187 | Validation | Empty reasons are accepted | `""` and `"   "` reasons on Project work, Meetings, Break and PTO rows → no errors; an off-step time or an overlap with an empty reason gives only those errors, no reason message (D-128) |
| T-188 | Grid | Week saved and submitted without reasons | Work, Break and leave slots with no reason and one with only spaces → saved with blank reasons (one slot keeps "Release"), then submitted; read-only dialogs of cells without reasons have no Reason column; a cell with one reasoned and one unreasoned slot shows the column with "Release" and one empty cell (D-128) |
| T-189 | Change request | Edit directly without a reason; requests and rejections still need theirs | The manager saves Monday 09:00–17:30 with no reason → saved blank; the UPDATE audit row records `"reason": ""`; the employee's read-only dialog shows 17:30 and no Reason column; `raise_request` with only spaces → "Explain what needs to change."; `reject_period` with only spaces → "Write a comment…", nothing decided (D-128, D-07) |
| T-190 | E2E | Time without a reason in a real browser | The Reason field is still offered; Start/End only → the cell shows 8.00, Save draft → Draft with no errors (reason saved blank); Submit → Submitted; the read-only dialog shows 09:00 and 17:00 and no Reason column (D-128) |
| T-191 | Grid rows | Delete a row with slots | PRJ-001 with 3 slots (6.50 h) and a Meetings row: the re-drawn grid has only Meetings, footer and week total 1.00, notice "Deleted PRJ-001 Customer Portal / Project work (3 time slots). Save to keep this change."; nothing saved by the action; after Save draft only the meeting is saved (D-129) |
| T-192 | Grid rows | Delete an empty row and a Break row | An added row without slots disappears ("Deleted Training."); deleting the Break row keeps Total worked hours 3.00; after saving the day summary shows Break 0:00 (D-129) |
| T-193 | Grid rows | Change project | PRJ-001 → PRJ-002: both slots keep their index, day, times and reason (one empty) under PRJ-002; the old row is gone; notice "Moved 2 time slots to PRJ-002 Mobile App / Project work…"; saved entries are PRJ-002 with the same times and reasons (D-130) |
| T-194 | Grid rows | Change into an existing row merges; overlaps still refused | PRJ-001 09:00–12:00 into the existing PRJ-002 row → one PRJ-002 row with both Monday slots, notice "…merged with its existing row…", saves; with PRJ-002 11:00–13:00 the merged week is refused on save with "Mon 19 Oct: 09:00–12:00 PRJ-002 and 11:00–13:00 PRJ-002 overlap." on the cell, nothing saved (D-38, D-130) |
| T-195 | Grid rows | Allowed changes | Project work → Meetings (worked unchanged), → Break (worked 0, not counted), Break → Project work (counted again), PTO → Sick; Project work → PTO, PTO → Meetings, unknown category, inactive project, unknown row and an unknown action → 400 with the reason, nothing saved (D-18, D-130) |
| T-196 | Grid rows | Locked and other people's weeks refused | The employee's endpoint: a submitted week and a past unsubmitted (locked) week → 403, GET → 405, the open week → 200. Edit directly's endpoint: the employee themselves and a manager outside the tree → 403, the manager → 200, after the request is handled → 403, GET → 405; the saved week is never touched (D-129, D-47) |
| T-197 | Change request | Row actions in Edit directly are audited | The manager moves PRJ-001 to PRJ-002 and deletes the Meetings row (no audit row yet), then "Save and submit for the employee" → exactly one UPDATE audit row (actor manager, linked to the request) with before PRJ-001 + Meetings and after PRJ-002 09:00–17:00; request EDITED, week SUBMITTED (D-49, D-129) |
| T-198 | Payroll | A paid week corrected by Delete row | A paid week of 42 h (2 h overtime from a Meetings 17:00–19:00 row): change request → Edit directly → Delete row → save → re-approval: v1 SUPERSEDED (still paid), v2 SETTLED 40 h, one adjustment overtime −2.00 h, total −2.00, carried to the next unexported period, reason from the request (D-118–D-122, D-129) |
| T-199 | Grid | Row-action markup | Editable week: "⋮" buttons named "Row actions for PRJ-001 Customer Portal" and "Row actions for PTO", `data-rows-url` set; a work row's Change dialog offers Project work, Meetings, Training, Other and Break with its project selected, a leave row's only PTO, Sick, Holiday; the Delete dialog reads "Delete PRJ-001 Customer Portal? This removes 2 time slots (7.00 h) from this week." (leave: "1 leave entry (8.00 h)"); every slot has an editable Reason input; a submitted week has no row menu (D-128, D-129, D-130) |
| T-200 | E2E | Change and delete rows in a real browser | Menus opened with real clicks and checked to be on top (T-202's check); PRJ-001 09:00–12:00 → ⋮ → Change project / category (Category focused) → PRJ-002: the dialog closes, one PRJ-002 row with 3.00, notice, focus on its ⋮, total 3.00. Meetings 13:00–14:00 (total 4.00) → ⋮ → Delete row: "Delete Meetings? This removes 1 time slot (1.00 h) from this week."; Esc closes and focus returns to ⋮; Delete row → row gone, total 3.00, day summary 3:00; Save draft saves one PRJ-002 entry 09:00–12:00 with its reason (D-129) |
| T-201 | Hardening | Static files are revalidated | With DEBUG off and on, anonymous: `grid.js`, `theme.css` and `htmx.min.js` answer 200 with `Cache-Control: no-cache`, and 304 (still `no-cache`) to If-Modified-Since = their Last-Modified; a missing file is 404 (D-131) |
| T-202 | E2E | Row menus in a real browser, laptop (1280×800) and narrow (390×844) | Each row's ⋮ sits right of the row name on its first line; a real click opens the menu, aligned to ⋮'s start; both items are visible, inside the window and the top element (`document.elementFromPoint`) at their left, middle and right; Esc closes it and focus stays on ⋮. Items open their dialog on a real click on the first row, after a cell edit, after Change row re-drew the grid (another row), after deleting an empty row, and on a row added afterwards; with the keyboard (Enter, then Space, with the arrow keys); Esc closes each dialog and focus returns to ⋮. The last row at the bottom of the window and the grid scrolled sideways still give an unclipped menu on top (D-129, D-131) |
| T-203 | Payroll | Approval deadline | Sep 27 – Oct 10 → Monday Oct 12, 12:00 company time; Oct 25 – Nov 7 (clocks go back) → Mon Nov 9 12:00 CST; a custom setting (3 days, 09:30) moves it; the Approvals page shows "Approve by Monday, Oct 12, 12:00 PM" and one "Overdue" badge (DEV2 pending, DEV1 approved); the current period's deadline is in the future and nothing is overdue (D-133) |
| T-204 | Payroll | Who must be approved, company-wide | Everyone active plus an inactive employee with a timesheet in the period and one hired mid-period; not someone who left before it, an inactive employee without a timesheet or someone hired after it; a manager's approvals list is the same rule for their reports; the pending list shows "Priya Shah" for DEV1 and "HR / an admin" for the CEO, with the reason ("Week 1 is locked — unlock it first.") (D-54, D-134) |
| T-205 | Payroll | OPEN → READY | Before the deadline with 9 of 10 approved: OPEN, "1 of 10 people are not approved yet."; the last approval → READY (everyone approved); an open change request → OPEN again until the deadline, then READY (deadline); a running period stays OPEN; an approval whose payroll write never ran keeps the period OPEN ("…run sync_payroll") and Finalize is refused (D-65, D-133) |
| T-206 | Payroll | Line values | DEV1's Week 1 / Week 2 columns equal the PayrollWeek records (40 h; 40 h regular + 5 h overtime + 4 h PTO); the 1 h Break appears nowhere; period total 89.00; approver Priya Shah; the totals row adds every line (169.00 pay total) (D-45, D-134) |
| T-207 | Payroll | Finalize & export | Refused while OPEN and for a running period; at READY (deadline) the POST saves a FINALIZED register EXP-0001 with 10 lines (9 of 10 approved), finalized by PAYROLL; exactly the period's records EXPORTED in EXP-0001 and listed on the lines; one EXPORT audit row (lines, records, total); a second finalize refused, nothing left to export (D-135) |
| T-208 | Payroll | Not approved by the deadline | After finalizing, DEV2 (submitted) has a 0.00 line "Waiting for manager approval", OPS1 (nothing submitted) "Missed – not submitted"; no timesheet status changes; DEV2 approved later → both weeks CURRENT, carried as late approvals into the next register (80.00 carry, original weeks Sep 27 and Oct 4) and exported in its batch only; the first register's line stays 0.00 (D-134, D-136) |
| T-209 | Payroll | Corrections carry into the next open register | After a PAID register for Sep 13: +2 h overtime (DEV1) and −1.50 h (DEV2) corrections show in Sep 27's carry-forward with their original week; a carry-only person gets a "Carry-forward only" line; the PAID register is unchanged; finalizing Sep 27 exports the adjustments in its batch; afterwards carry_period skips Sep 27 (D-136) |
| T-210 | Payroll | Registers are append-only | Changing a frozen field, paying without `paid_at`, PAID → FINALIZED, changing a line, deleting a register or line, bulk update/delete, and creating a register that isn't FINALIZED are all refused (D-132) |
| T-211 | Payroll | Mark as paid | Pays the register and its batch's 2 week records and 1 adjustment; PAY audit row with the counts; a second Mark as paid does nothing (no second audit row) (D-135) |
| T-212 | Payroll | Register and detailed CSVs | No download before finalizing (404); Register CSV `payroll-register_2026-09-27_to_2026-10-10_EXP-0002.csv` with exactly the register columns, a formula-like name escaped, DEV1 40.00 / 80.00 / carry 0.00 / pay 80.00, the CEO "Missed – not submitted" 0.00; detailed CSV `payroll-detail_…` with today's columns; all periods `payroll-registers_2026-09-13_to_2026-10-10.csv` with period_start, period_end, batch; date ranges include the period containing "from"; downloads change no status and write no audit row (D-68, D-135) |
| T-213 | Payroll | Pay period pages | `/payroll/` lists Sep 27 (Ready, 2 of 10, 160.00, downloads "after finalizing") above Sep 13 (Paid, 1 of 10, EXP-0001, Register CSV); the period page shows the status, the finalize dialog and the pending list; a mid-period date redirects to its period; a running period is 404; employees, managers and directors get 403 on the page and on Finalize (D-138) |
| T-214 | Payroll | `build_registers` for earlier exports | Sep 13 exported and paid the old way → PAID register EXP-0001; Sep 27 exported twice (EXP-0002, EXP-0003) → FINALIZED "EXP-0002+EXP-0003" with DEV1 and DEV2 lines only; OPS1, approved after both exports, is carried to the next register; finalized by "build_registers", one PUBLISH audit row each; a second run builds nothing (D-137) |
| T-215 | Payroll | `sync_payroll` builds missing registers | The banner shows "1 exported pay period without a register"; sync builds it (registers = 1) and the banner goes; a second sync builds none; SYNC audit rows report 1 then 0 (D-137) |
| T-216 | E2E | Register from the last approval to Paid | Clock Monday 09:00 before the deadline, everyone approved but DEV2: the register is Open, the pending list shows Sara Ng and her approver Priya Shah, Finalize & export disabled; the manager approves Sara in the browser → Ready ("Everyone who must be approved…"); Finalize & export in the dialog → "exported as batch EXP-0001", Finalized & exported with a line per person; the Register CSV downloads as `payroll-register_2026-09-27_to_2026-10-10_EXP-0001.csv` with one row per person; Mark as paid → Paid; the pay period list shows Paid, all approved, EXP-0001 (D-132–D-135) |

### Status of every test (Phase 12, updated for Changes 1–8)

Result of `bash scripts/test_all.sh` on October 26, 2026 (after Change 8) (fixed clocks, test databases only): **293 test cases, all passed** (276 unit + integration, 17 e2e; parametrised cases counted separately), including the catalogued tests T-01–T-156 below (Change 1 adds T-157–T-159, Change 2 T-160–T-167, Change 3 T-168–T-172, Change 4 T-173–T-182, Change 5 T-183–T-186, Change 6 T-187–T-190, Change 7 T-191–T-202 and Change 8 T-203–T-216, all passing; tests set the Sunday pay-period anchor themselves); the rest are helper checks without an ID (D-17). Coverage (unit + integration): **98.15 %** of the whole project (target ≥ 80 %); every `*/services/*` module ≥ 95 % (target ≥ 90 %). Parametrised tests count once here.

| ID | Area | Test (`tests/…`) | Status |
|---|---|---|---|
| T-01 | Sign-up | `unit/test_signup.py::test_wrong_domain_is_refused` | ✅ Pass |
| T-02 | Sign-up | `unit/test_signup.py::test_email_not_in_directory_is_refused_with_contact_hr` | ✅ Pass |
| T-03 | Sign-up | `unit/test_signup.py::test_inactive_employee_is_refused` | ✅ Pass |
| T-04 | Sign-up | `unit/test_signup.py::test_existing_account_is_refused` | ✅ Pass |
| T-05 | Sign-up | `integration/test_auth_views.py::test_signup_creates_account_with_lowercase_email` | ✅ Pass |
| T-06 | Password | `unit/test_passwords.py::test_password_is_hashed_with_argon2_never_plain_text` | ✅ Pass |
| T-07 | Password | `unit/test_passwords.py::test_same_password_gives_different_hashes` | ✅ Pass |
| T-08 | Password | `unit/test_passwords.py::test_short_or_common_passwords_are_rejected` | ✅ Pass (3 cases) |
| T-09 | Login | `integration/test_auth_views.py::test_correct_password_logs_in` | ✅ Pass |
| T-10 | Login | `integration/test_auth_views.py::test_five_wrong_attempts_lock_the_account_for_15_minutes` | ✅ Pass |
| T-11 | Login | `integration/test_auth_views.py::test_inactive_employee_cannot_log_in` | ✅ Pass |
| T-12 | Calendar | `unit/test_calendar.py::test_week_start_for_every_day_is_sunday` | ✅ Pass |
| T-13 | Calendar | `unit/test_calendar.py::test_week_still_open_at_1159` | ✅ Pass |
| T-14 | Calendar | `unit/test_calendar.py::test_week_locked_at_noon` | ✅ Pass |
| T-15 | Calendar | `unit/test_calendar.py::test_deadline_stays_noon_local_across_daylight_saving` | ✅ Pass |
| T-16 | Calendar | `unit/test_calendar.py::test_pay_period_across_year_boundary` | ✅ Pass |
| T-17 | Validation | `unit/test_validation.py::test_times_and_hours_must_use_15_minute_steps` | ✅ Pass |
| T-18 | Validation | `unit/test_validation.py::test_day_total_over_24_hours_is_rejected` | ✅ Pass |
| T-19 | Validation | `unit/test_validation.py::test_date_outside_week_or_inactive_project_is_rejected` | ✅ Pass |
| T-20 | Timesheet | `integration/test_timesheet_flow.py::test_save_draft_then_submit_before_deadline` | ✅ Pass |
| T-21 | Timesheet | `integration/test_timesheet_flow.py::test_employee_cannot_edit_after_submitting` | ✅ Pass |
| T-22 | Timesheet | `integration/test_timesheet_flow.py::test_unsubmitted_week_locks_at_deadline_and_counts_as_missed` | ✅ Pass |
| T-23 | Change request | `integration/test_change_requests.py::test_request_is_visible_to_own_manager_only` | ✅ Pass |
| T-24 | Change request | `integration/test_change_requests.py::test_unlock_reopens_until_later_of_48h_and_deadline` | ✅ Pass |
| T-25 | Change request | `integration/test_change_requests.py::test_edit_directly_writes_before_and_after` | ✅ Pass |
| T-26 | Permissions | `integration/test_layout.py::test_employee_is_refused_manager_and_payroll_pages` | ✅ Pass |
| T-27 | Permissions | `unit/test_permissions.py::test_director_sees_indirect_reports_manager_only_own_tree` | ✅ Pass |
| T-28 | Permissions | `unit/test_permissions.py::test_reporting_tree_survives_a_cycle` | ✅ Pass |
| T-29 | Approvals | `integration/test_approvals.py::test_approve_blocked_while_a_week_is_draft_or_locked` | ✅ Pass |
| T-30 | Approvals | `integration/test_approvals.py::test_approving_both_weeks` | ✅ Pass |
| T-31 | Approvals | `integration/test_approvals.py::test_reject_needs_a_comment_and_reopens_both_weeks` | ✅ Pass |
| T-32 | Approvals | `integration/test_approvals.py::test_non_manager_cannot_approve` | ✅ Pass |
| T-33 | Payroll | `integration/test_payroll_publish.py::test_approval_publishes_two_week_records` | ✅ Pass |
| T-34 | Payroll | `integration/test_payroll_publish.py::test_overtime_and_pto_split` | ✅ Pass |
| T-35 | Payroll | `integration/test_payroll_publish.py::test_publish_twice_creates_no_duplicates` | ✅ Pass |
| T-36 | Payroll | `integration/test_payroll_publish.py::test_approved_week_edited_later_gets_a_new_version` | ✅ Pass |
| T-37 | Payroll | `integration/test_payroll_pages.py::test_export_csv` | ✅ Pass |
| T-38 | Payroll | `integration/test_payroll_pages.py::test_managers_and_employees_get_403` | ✅ Pass |
| T-39 | Payroll | `integration/test_payroll_pages.py::test_superseded_after_export_is_listed_in_corrections` | ✅ Pass |
| T-40 | Analytics | `integration/test_analytics.py::test_dashboard_numbers_for_known_data` | ✅ Pass |
| T-41 | Seed | `integration/test_seed_demo.py::test_seed_builds_the_demo_company` | ✅ Pass |
| T-42 | Seed | `integration/test_seed_demo.py::test_seed_refuses_to_run_twice` | ✅ Pass |
| T-43 | Change request | `integration/test_change_requests.py::test_week_unlocked_on_wednesday_stays_open_until_saturday_noon` | ✅ Pass |
| T-44 | Accounts | `unit/test_accounts.py::test_account_requires_an_employee` | ✅ Pass |
| T-45 | Accounts | `unit/test_accounts.py::test_create_user_takes_email_and_flags_from_employee` | ✅ Pass |
| T-46 | Accounts | `unit/test_accounts.py::test_createsuperuser_refuses_ineligible_employees` | ✅ Pass |
| T-47 | Accounts | `unit/test_accounts.py::test_createsuperuser_creates_admin_account_for_active_admin_employee` | ✅ Pass |
| T-48 | Accounts | `unit/test_accounts.py::test_admin_flag_controls_staff_and_superuser` | ✅ Pass |
| T-49 | Accounts | `unit/test_accounts.py::test_employee_status_controls_is_active` | ✅ Pass |
| T-50 | Accounts | `unit/test_accounts.py::test_email_change_in_directory_updates_account` | ✅ Pass |
| T-51 | Accounts | `unit/test_accounts.py::test_emails_stay_unique_regardless_of_case` | ✅ Pass |
| T-52 | Audit | `unit/test_audit.py::test_audit_row_needs_exactly_one_actor` | ✅ Pass |
| T-53 | Import | `integration/test_import_employees.py::test_import_creates_people_teams_and_manager_links` | ✅ Pass |
| T-54 | Import | `integration/test_import_employees.py::test_reimport_updates_in_place_and_syncs_account` | ✅ Pass |
| T-55 | Import | `integration/test_import_employees.py::test_invalid_csv_imports_nothing_and_lists_every_error` | ✅ Pass |
| T-56 | Seed | `integration/test_seed_demo.py::test_seed_approvals_follow_the_rules` | ✅ Pass |
| T-57 | Seed | `integration/test_seed_demo.py::test_seed_audit_rows_name_the_right_actor` | ✅ Pass |
| T-58 | Login | `integration/test_auth_views.py::test_every_page_requires_login_except_login_and_signup` | ✅ Pass |
| T-59 | Databases | `integration/test_auth_views.py::test_axes_and_main_tables_stay_out_of_payroll_database` | ✅ Pass |
| T-60 | Permissions | `unit/test_permissions.py::test_only_the_direct_manager_approves` | ✅ Pass |
| T-61 | Permissions | `unit/test_permissions.py::test_admins_approve_only_employees_without_a_manager` | ✅ Pass |
| T-62 | Permissions | `integration/test_layout.py::test_payroll_flag_adds_only_payroll_pages` | ✅ Pass |
| T-63 | Permissions | `integration/test_layout.py::test_payroll_user_who_manages_gets_manager_rights_for_own_tree` | ✅ Pass |
| T-64 | Layout | `integration/test_layout.py::test_menu_and_header_follow_roles` | ✅ Pass |
| T-65 | Profile | `integration/test_layout.py::test_profile_shows_directory_details_read_only` | ✅ Pass |
| T-66 | Profile | `integration/test_layout.py::test_password_change_keeps_session_and_audits_without_password_data` | ✅ Pass |
| T-67 | Validation | `unit/test_validation.py::test_project_entries_need_a_project_and_others_must_not_have_one` | ✅ Pass |
| T-68 | Validation | `unit/test_validation.py::test_entries_only_within_employment` | ✅ Pass |
| T-69 | Calendar | `unit/test_calendar.py::test_expected_minutes_are_prorated_for_partial_weeks` | ✅ Pass |
| T-70 | Timesheet | `unit/test_calendar.py::test_weeks_outside_employment_are_never_missed` | ✅ Pass |
| T-71 | Timesheet | `integration/test_timesheet_flow.py::test_submit_writes_audit_row` | ✅ Pass |
| T-72 | Validation | `unit/test_validation.py::test_end_must_be_after_start` | ✅ Pass |
| T-73 | Validation | `unit/test_validation.py::test_timed_rows_on_one_day_must_not_overlap` | ✅ Pass |
| T-74 | Validation | `unit/test_validation.py::test_reason_is_limited_to_255_characters` | ✅ Pass |
| T-75 | Validation | `unit/test_validation.py::test_break_has_times_and_never_a_project` | ✅ Pass |
| T-76 | Validation | `unit/test_validation.py::test_leave_is_hours_only_and_work_needs_times` | ✅ Pass |
| T-77 | Timesheet | `integration/test_timesheet_flow.py::test_hours_worked_excludes_break_and_leave` | ✅ Pass |
| T-78 | Timesheet | `integration/test_timesheet_flow.py::test_break_only_week_cannot_be_submitted` | ✅ Pass |
| T-79 | Timesheet | `integration/test_timesheet_flow.py::test_many_rows_on_one_day` | ✅ Pass |
| T-80 | Seed | `integration/test_seed_demo.py::test_seeded_entries_pass_the_entry_rules` | ✅ Pass |
| T-81 | Change request | `integration/test_change_requests.py::test_requests_only_on_submitted_locked_or_approved_weeks` | ✅ Pass |
| T-82 | Change request | `integration/test_change_requests.py::test_who_handles_a_request` | ✅ Pass |
| T-83 | Change request | `integration/test_change_requests.py::test_each_step_is_audited` | ✅ Pass |
| T-84 | Change request | `integration/test_change_requests.py::test_edit_directly_uses_the_same_rules` | ✅ Pass |
| T-85 | Change request | `integration/test_change_requests.py::test_changing_an_approved_week_resets_the_period` | ✅ Pass (2 cases) |
| T-86 | Timesheet | `integration/test_change_requests.py::test_reopened_past_week_is_editable_until_window_ends` | ✅ Pass |
| T-87 | Timesheet | `integration/test_change_requests.py::test_late_flag_is_decided_by_the_first_submission` | ✅ Pass |
| T-88 | Layout | `integration/test_change_requests.py::test_open_request_count_in_menu` | ✅ Pass |
| T-89 | Timesheet | `integration/test_entry_form.py::test_completely_empty_rows_are_ignored` | ✅ Pass (2 cases) |
| T-90 | Timesheet | `integration/test_entry_form.py::test_rerender_after_an_error_adds_no_rows` | ✅ Pass (2 cases) |
| T-91 | Timesheet | `integration/test_entry_form.py::test_hours_are_shown_for_every_row` | ✅ Pass (2 cases) |
| T-92 | Approvals | `integration/test_approvals.py::test_unlock_locked_week_from_approvals` | ✅ Pass |
| T-93 | Approvals | `integration/test_approvals.py::test_rejected_period_comes_back_after_resubmission` | ✅ Pass |
| T-94 | Approvals | `integration/test_approvals.py::test_approve_is_one_transaction_with_the_payroll_hook` | ✅ Pass |
| T-95 | Approvals | `integration/test_approvals.py::test_who_sees_and_approves_which_rows` | ✅ Pass |
| T-96 | Approvals | `integration/test_approvals.py::test_bulk_approve` | ✅ Pass |
| T-97 | Approvals | `integration/test_approvals.py::test_pay_period_dates` | ✅ Pass |
| T-98 | Approvals | `integration/test_approvals.py::test_flags` | ✅ Pass |
| T-99 | Approvals | `integration/test_approvals.py::test_forbidden_cases` | ✅ Pass |
| T-100 | Approvals | `integration/test_approvals.py::test_period_partly_outside_employment` | ✅ Pass |
| T-101 | Approvals | `integration/test_approvals.py::test_open_change_request_blocks_approval` | ✅ Pass |
| T-102 | Timesheet | `integration/test_approvals.py::test_week_page_shows_approval_status` | ✅ Pass |
| T-103 | Payroll | `unit/test_payroll_split.py::test_overtime_rule` | ✅ Pass |
| T-104 | Payroll | `integration/test_payroll_publish.py::test_payroll_records_are_append_only` | ✅ Pass |
| T-105 | Payroll | `integration/test_payroll_publish.py::test_deactivated_employee_is_published_and_paid` | ✅ Pass |
| T-106 | Payroll | `integration/test_payroll_publish.py::test_publish_and_sync_are_idempotent` | ✅ Pass |
| T-107 | Payroll | `integration/test_payroll_publish.py::test_payroll_failure_after_commit_is_repaired_by_sync` | ✅ Pass |
| T-108 | Payroll | `integration/test_payroll_publish.py::test_main_rollback_writes_nothing_to_payroll` | ✅ Pass |
| T-109 | Payroll | `integration/test_payroll_publish.py::test_supersede_failure_is_repaired_by_sync` | ✅ Pass |
| T-110 | Payroll | `integration/test_payroll_pages.py::test_csv_cells_are_spreadsheet_safe` | ✅ Pass |
| T-111 | Payroll | `integration/test_payroll_pages.py::test_who_can_open_payroll_pages` | ✅ Pass |
| T-112 | Payroll | `integration/test_payroll_publish.py::test_mark_paid_moves_only_exported_records` | ✅ Pass |
| T-113 | Payroll | `integration/test_payroll_publish.py::test_backup_db_copies_both_databases` | ✅ Pass |
| T-114 | Seed | `integration/test_seed_demo.py::test_seed_fills_the_payroll_database` | ✅ Pass |
| T-115 | Analytics | `integration/test_analytics.py::test_range_filter` | ✅ Pass |
| T-116 | Analytics | `integration/test_analytics.py::test_on_time_late_missed_edge_cases` | ✅ Pass |
| T-117 | Analytics | `integration/test_analytics.py::test_new_hire_and_deactivated_employee` | ✅ Pass |
| T-118 | Analytics | `integration/test_analytics.py::test_dashboard_overtime_matches_payroll` | ✅ Pass |
| T-119 | Analytics | `integration/test_analytics.py::test_only_own_data` | ✅ Pass |
| T-120 | Analytics | `integration/test_analytics.py::test_empty_state` | ✅ Pass |
| T-121 | Analytics | `integration/test_analytics.py::test_viewing_writes_nothing_and_queries_are_bounded` | ✅ Pass |
| T-122 | Analytics | `integration/test_analytics.py::test_categories_break_outcomes_and_current_week` | ✅ Pass |
| T-123 | Team | `integration/test_team.py::test_team_metrics_for_known_data` | ✅ Pass |
| T-124 | Team | `integration/test_team.py::test_utilization_rule` | ✅ Pass |
| T-125 | Team | `integration/test_team.py::test_whole_tree_vs_direct_and_team_filter` | ✅ Pass |
| T-126 | Team | `integration/test_team.py::test_access_rules` | ✅ Pass |
| T-127 | Team | `integration/test_team.py::test_admin_sees_everyone` | ✅ Pass |
| T-128 | Team | `integration/test_team.py::test_this_weeks_compliance` | ✅ Pass |
| T-129 | Team | `integration/test_team.py::test_inactive_employees_only_with_timesheets` | ✅ Pass |
| T-130 | Team | `integration/test_team.py::test_drill_down_is_read_only` | ✅ Pass |
| T-131 | Team | `integration/test_team.py::test_viewing_writes_nothing` | ✅ Pass |
| T-132 | Team | `integration/test_team.py::test_query_count_is_fixed_for_large_teams` | ✅ Pass |
| T-133 | Admin | `integration/test_admin_edit.py::test_employee_edit_is_audited` | ✅ Pass |
| T-134 | Admin | `integration/test_admin_edit.py::test_add_and_edit_teams_projects_and_employees` | ✅ Pass |
| T-135 | Admin | `integration/test_admin_edit.py::test_workflow_records_are_read_only` | ✅ Pass |
| T-136 | Admin | `integration/test_admin_edit.py::test_nothing_can_be_deleted` | ✅ Pass |
| T-137 | Admin | `integration/test_admin_edit.py::test_deactivate` | ✅ Pass |
| T-138 | Admin | `integration/test_admin_edit.py::test_deactivate_and_reactivate_rules` | ✅ Pass |
| T-139 | Admin | `integration/test_admin_edit.py::test_email_and_flag_sync` | ✅ Pass |
| T-140 | Admin | `integration/test_admin_edit.py::test_safety_rules` | ✅ Pass |
| T-141 | Admin | `integration/test_admin_edit.py::test_password_reset` | ✅ Pass |
| T-142 | Admin | `integration/test_admin_csv.py::test_csv_import_in_admin` | ✅ Pass |
| T-143 | Admin | `integration/test_admin_csv.py::test_csv_export_round_trip` | ✅ Pass |
| T-144 | Admin | `integration/test_admin_edit.py::test_only_directory_admins_reach_admin` | ✅ Pass |
| T-145 | Admin | `integration/test_admin_edit.py::test_search_and_filters` | ✅ Pass |
| T-146 | E2E | `e2e/test_e2e_flows.py::test_signup_refused_then_accepted` | ✅ Pass |
| T-147 | E2E | `e2e/test_e2e_flows.py::test_save_draft_then_submit_before_the_deadline` | ✅ Pass |
| T-148 | E2E | `e2e/test_e2e_flows.py::test_week_locks_after_the_deadline` | ✅ Pass |
| T-149 | E2E | `e2e/test_e2e_flows.py::test_change_request_then_manager_edits_directly` | ✅ Pass |
| T-150 | E2E | `e2e/test_e2e_flows.py::test_approve_then_payroll_sees_the_records` | ✅ Pass |
| T-151 | E2E | `e2e/test_e2e_flows.py::test_reject_with_comment_then_resubmit` | ✅ Pass |
| T-152 | E2E | `e2e/test_e2e_flows.py::test_payroll_export_and_mark_paid` | ✅ Pass |
| T-153 | E2E | `e2e/test_e2e_flows.py::test_hr_deactivates_an_employee` | ✅ Pass |
| T-154 | E2E | `e2e/test_e2e_flows.py::test_hr_password_reset_forces_a_change` | ✅ Pass |
| T-155 | E2E | `e2e/test_e2e_flows.py::test_forbidden_pages` | ✅ Pass |
| T-156 | Hardening | `integration/test_hardening.py::test_debug_off_serves_static_and_friendly_errors` | ✅ Pass |
| T-157 | UI | `integration/test_ui_theme.py::test_theme_stylesheet_is_loaded_and_served` | ✅ Pass |
| T-158 | UI | `integration/test_ui_theme.py::test_one_status_badge_component` | ✅ Pass |
| T-159 | UI | `integration/test_ui_theme.py::test_theme_contrast_meets_wcag_aa` | ✅ Pass |
| T-160 | Grid | `integration/test_grid.py::test_grid_layout_and_totals` | ✅ Pass |
| T-161 | Grid | `integration/test_grid.py::test_add_row` | ✅ Pass |
| T-162 | Grid | `integration/test_grid.py::test_multi_slot_cell` | ✅ Pass |
| T-163 | Grid | `integration/test_grid.py::test_leave_cell` | ✅ Pass |
| T-164 | Grid | `integration/test_grid.py::test_overlap_error_is_shown_on_the_right_cells` | ✅ Pass |
| T-165 | Grid | `integration/test_grid.py::test_read_only_grids` | ✅ Pass |
| T-166 | Grid | `integration/test_grid.py::test_existing_week_renders_the_same` | ✅ Pass |
| T-167 | E2E | `e2e/test_e2e_flows.py::test_weekly_grid_in_the_browser` | ✅ Pass |
| T-168 | Calendar | `unit/test_calendar.py::test_week_boundaries_saturday_night_and_sunday_midnight` | ✅ Pass |
| T-169 | Timesheet | `integration/test_sunday_week.py::test_deadline_is_on_the_last_day` | ✅ Pass |
| T-170 | Calendar | `unit/test_calendar.py::test_pay_period_anchor_must_be_a_sunday` | ✅ Pass |
| T-171 | Timesheet | `integration/test_sunday_week.py::test_non_sunday_dates_redirect_to_their_week` | ✅ Pass |
| T-172 | Calendar | `integration/test_sunday_week.py::test_daylight_saving_week` | ✅ Pass |
| T-173 | Payroll | `integration/test_adjustments.py::test_positive_overtime_adjustment_after_payment` | ✅ Pass |
| T-174 | Payroll | `integration/test_adjustments.py::test_negative_adjustment` | ✅ Pass |
| T-175 | Payroll | `integration/test_adjustments.py::test_no_adjustment_when_the_old_version_was_never_exported` | ✅ Pass |
| T-176 | Payroll | `integration/test_adjustments.py::test_several_corrections_of_the_same_week` | ✅ Pass |
| T-177 | Payroll | `integration/test_adjustments.py::test_new_full_version_is_never_exported_twice` | ✅ Pass |
| T-178 | Payroll | `integration/test_adjustments.py::test_carry_forward_period` | ✅ Pass |
| T-179 | Payroll | `integration/test_adjustments.py::test_csv_totals_mark_paid_and_corrections` | ✅ Pass |
| T-180 | Payroll | `integration/test_adjustments.py::test_sync_creates_missing_adjustments_idempotently` | ✅ Pass |
| T-181 | Payroll | `integration/test_adjustments.py::test_adjustments_are_append_only_and_audited` | ✅ Pass |
| T-182 | Payroll | `integration/test_adjustments.py::test_settled_week_links_to_the_period_that_paid_its_difference` | ✅ Pass |
| T-183 | E2E | `e2e/test_e2e_flows.py::test_add_row_for_an_existing_row_points_at_it` | ✅ Pass |
| T-184 | Grid | `integration/test_grid.py::test_two_slots_for_one_project_on_one_day` | ✅ Pass |
| T-185 | Grid | `integration/test_grid.py::test_overlapping_third_slot_is_refused_on_its_cell` | ✅ Pass |
| T-186 | Grid | `integration/test_grid.py::test_multi_slot_hint` | ✅ Pass |
| T-187 | Validation | `unit/test_validation.py::test_empty_reasons_are_accepted` | ✅ Pass |
| T-188 | Grid | `integration/test_grid.py::test_week_without_reasons` | ✅ Pass |
| T-189 | Change request | `integration/test_change_requests.py::test_edit_directly_without_a_reason` | ✅ Pass |
| T-190 | E2E | `e2e/test_e2e_flows.py::test_time_without_a_reason` | ✅ Pass |
| T-191 | Grid rows | `integration/test_row_actions.py::test_delete_a_row_with_slots` | ✅ Pass |
| T-192 | Grid rows | `integration/test_row_actions.py::test_delete_an_empty_row_and_a_break_row` | ✅ Pass |
| T-193 | Grid rows | `integration/test_row_actions.py::test_change_project` | ✅ Pass |
| T-194 | Grid rows | `integration/test_row_actions.py::test_change_into_an_existing_row_merges` | ✅ Pass |
| T-195 | Grid rows | `integration/test_row_actions.py::test_allowed_changes` | ✅ Pass |
| T-196 | Grid rows | `integration/test_row_actions.py::test_locked_and_other_peoples_weeks_are_refused` | ✅ Pass |
| T-197 | Change request | `integration/test_row_actions.py::test_row_actions_in_edit_directly_are_audited` | ✅ Pass |
| T-198 | Payroll | `integration/test_adjustments.py::test_paid_week_corrected_by_deleting_a_row` | ✅ Pass |
| T-199 | Grid | `integration/test_row_actions.py::test_row_action_markup` | ✅ Pass |
| T-200 | E2E | `e2e/test_e2e_flows.py::test_change_and_delete_rows` | ✅ Pass |
| T-201 | Hardening | `integration/test_ui_theme.py::test_static_files_are_revalidated_on_every_page_load` | ✅ Pass (2 cases) |
| T-202 | E2E | `e2e/test_e2e_flows.py::test_row_menus_in_a_real_browser` | ✅ Pass (2 cases) |
| T-203 | Payroll | `integration/test_payroll_register.py::test_approval_deadline` | ✅ Pass |
| T-204 | Payroll | `integration/test_payroll_register.py::test_who_must_be_approved_company_wide` | ✅ Pass |
| T-205 | Payroll | `integration/test_payroll_register.py::test_open_becomes_ready` | ✅ Pass |
| T-206 | Payroll | `integration/test_payroll_register.py::test_line_values_come_from_the_week_records` | ✅ Pass |
| T-207 | Payroll | `integration/test_payroll_register.py::test_finalize_and_export` | ✅ Pass |
| T-208 | Payroll | `integration/test_payroll_register.py::test_people_not_approved_by_the_deadline` | ✅ Pass |
| T-209 | Payroll | `integration/test_payroll_register.py::test_corrections_carry_into_the_next_open_register` | ✅ Pass |
| T-210 | Payroll | `integration/test_payroll_register.py::test_registers_are_append_only` | ✅ Pass |
| T-211 | Payroll | `integration/test_payroll_register.py::test_mark_as_paid` | ✅ Pass |
| T-212 | Payroll | `integration/test_payroll_register.py::test_register_csv_downloads` | ✅ Pass |
| T-213 | Payroll | `integration/test_payroll_register.py::test_payroll_pages` | ✅ Pass |
| T-214 | Payroll | `integration/test_payroll_register.py::test_build_registers_for_earlier_exports` | ✅ Pass |
| T-215 | Payroll | `integration/test_payroll_register.py::test_sync_payroll_builds_missing_registers` | ✅ Pass |
| T-216 | E2E | `e2e/test_e2e_flows.py::test_register_from_last_approval_to_paid` | ✅ Pass |

### Example test code (the style Claude Code should follow)
```python
# tests/unit/test_calendar.py
from datetime import date, datetime
from zoneinfo import ZoneInfo
from timesheets.services.calendar import deadline_for, effective_status

TZ = ZoneInfo("America/Chicago")

def test_deadline_is_saturday_noon_local():
    """Helper check: deadline_for returns Saturday 12:00 local time."""
    assert deadline_for(date(2026, 10, 19), TZ) == datetime(2026, 10, 24, 12, 0, tzinfo=TZ)

def test_week_still_open_at_1159(draft_sheet_week_of_oct_19):
    """T-13: week still open at Saturday 11:59:59."""
    now = datetime(2026, 10, 24, 11, 59, 59, tzinfo=TZ)
    assert effective_status(draft_sheet_week_of_oct_19, now) == "DRAFT"

def test_week_locked_at_noon(draft_sheet_week_of_oct_19):
    """T-14: week locked at Saturday 12:00:00."""
    now = datetime(2026, 10, 24, 12, 0, 0, tzinfo=TZ)
    assert effective_status(draft_sheet_week_of_oct_19, now) == "LOCKED"
```

```python
# tests/unit/test_passwords.py
import pytest
from tests.factories import UserFactory

@pytest.mark.django_db
def test_password_is_hashed_with_argon2_never_plain_text():
    """T-06: stored password is an Argon2 hash, never the typed password."""
    user = UserFactory(password="Correct-Horse-42!")
    assert user.password.startswith("argon2")
    assert "Correct-Horse-42!" not in user.password
    assert user.check_password("Correct-Horse-42!")

@pytest.mark.django_db
def test_same_password_gives_different_hashes():
    """T-07: same password for two users gives different hashes (random salt)."""
    a = UserFactory(password="Same-Password-123")
    b = UserFactory(password="Same-Password-123")
    assert a.password != b.password
```

```python
# tests/integration/test_payroll_publish.py
import pytest
from payroll.models import PayrollWeek
from payroll.services.publish import publish_period

@pytest.mark.django_db(databases=["default", "payroll"])
def test_overtime_and_pto_split(approved_period_45h_worked_8h_pto):
    """T-34: 45 h worked + 8 h PTO with 40 h expected → 40 regular, 5 overtime, 8 PTO."""
    publish_period(approved_period_45h_worked_8h_pto)
    week = PayrollWeek.objects.using("payroll").get(status="CURRENT", week_start="2026-10-05")
    assert (week.regular_minutes, week.overtime_minutes, week.pto_minutes) == (2400, 300, 480)

@pytest.mark.django_db(databases=["default", "payroll"])
def test_publish_twice_creates_no_duplicates(approved_period_45h_worked_8h_pto):
    """T-35: running publish_period twice creates no duplicates."""
    publish_period(approved_period_45h_worked_8h_pto)
    publish_period(approved_period_45h_worked_8h_pto)
    assert PayrollWeek.objects.using("payroll").filter(status="CURRENT").count() == 2
```

```python
# tests/e2e/test_e2e_flows.py
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
def test_signup_refused_for_unknown_email(page: Page, live_server):
    """T-146: E2E sign-up refused for an email that is not in the directory."""
    page.goto(f"{live_server.url}/signup/")
    page.get_by_label("Email").fill("nobody@yourcompany.com")
    page.get_by_label("Password", exact=True).fill("Long-Enough-Pass-1")
    page.get_by_label("Confirm password").fill("Long-Enough-Pass-1")
    page.get_by_role("button", name="Sign up").click()
    expect(page.get_by_text("not in the company employee directory")).to_be_visible()
```

### Coverage targets
- `*/services/*` (business rules): **≥ 90%** line coverage
- Whole project: **≥ 80%**
- Report: `uv run pytest --cov --cov-report=html` → open `htmlcov/index.html`

### One-command test run (`scripts/test_all.sh`)
Runs, in order, and stops at the first failure:
1. `uv run ruff check .` — code style and common bugs
2. `uv run python manage.py makemigrations --check --dry-run` — no forgotten migrations
3. `uv run python manage.py check` — Django configuration
4. `uv run pytest -m "not e2e" --cov --cov-fail-under=80` — unit + integration with coverage
5. `uv run pytest -m e2e` — browser tests, **mandatory** since Phase 12 (D-95): "no tests collected" fails like any other error. Install Chromium once with `uv run playwright install chromium`. Extra arguments go to this step, e.g. `bash scripts/test_all.sh --browser-channel chrome` to use an installed Google Chrome instead.

```bash
bash scripts/test_all.sh
```
Run it at the end of **every** phase, before committing.

## B.12 Decisions log

Decisions made after the spec review (D-01–D-20 on October 21, 2026; D-21–D-45 on October 22, 2026; D-46–D-63 on October 23, 2026; D-64–D-117 on October 24, 2026; D-118–D-126 on October 25, 2026). **If B.12 conflicts with anything else in this guide, B.12 wins.**

| ID | Area | Decision | Affects |
|---|---|---|---|
| D-01 | Setup | `test_all.sh`: when no tests are marked `e2e`, skip the e2e step and print `e2e: skipped - no e2e tests yet`; treat pytest exit code 5 as success **only** for that step. Phase 12 installs Chromium and makes e2e mandatory — done, see D-95. | B.11, C.4 P1/P12 |
| D-02 | Setup | Custom `UserManager` with email login. `create_user` / `create_superuser` require an employee. `createsuperuser` asks for an `employee_code` that must exist, be ACTIVE and have no account. Normal accounts come from `seed_demo` or sign-up. | B.6, C.4 P1 |
| D-03 | Setup | Add `DJANGO_ALLOWED_HOSTS` to `.env.example` (default `127.0.0.1,localhost`). | B.1 `.env`, C.4 P1 |
| D-04 | Setup | Every app uses a services package: `<app>/services/<module>.py` (e.g. `payroll/services/publish.py`, `analytics/services/metrics.py`). | B.6, B.9, B.11, C.4 |
| D-05 | Setup | Git: the project owner runs `git init` and the first commit before Phase 0. | C.1 |
| D-06 | Timesheet status | Only SUBMITTED weeks can be approved. A LOCKED week must first be unlocked (through a change request, or by the manager directly from the approval page, which creates a manager-authored ChangeRequest and an audit entry) and then submitted. | B.1, B.4 FR-7, B.5, B.6, B.7, B.8, B.9, B.11 T-29 |
| D-07 | Timesheet status | Reject sets both weeks to REOPENED with `reopen_until` set per D-21. | B.4 FR-7, B.5, B.11 T-31 |
| D-08 | Timesheet status | When a reopen window (unlock or reject, length per D-21) ends without resubmission, the week becomes LOCKED. A week submitted after its original deadline keeps `is_late = True`. | B.1, B.4 FR-8/FR-9, B.5, B.9, B.11 T-24 |
| D-09 | Timesheet status | The Saturday 12:00 deadline is intended. Weekend hours may be entered in advance; any change after submitting goes through a change request. | B.1, B.4 FR-8 |
| D-10 | Timesheet status | `PeriodApproval` is the source of truth. Only `timesheets/services/approvals.py` may change `Timesheet.status` to or from APPROVED, in the same database transaction as the PeriodApproval change. | B.4 FR-9, B.5, B.6, B.9 |
| D-11 | Roles | Nobody can ever approve their own timesheet. Approver = direct manager. Admins approve only employees with no manager, never themselves (the CEO is approved by the HR admin). In B.3, Admin approves "top-level employees only". | B.1, B.3, B.4 FR-7, B.9 |
| D-12 | Roles | Roles add up. Payroll users are also employees (own timesheet, analytics, change requests). The payroll flag only adds `/payroll/` and never grants access to other people's timesheet details. A payroll user who is also a manager gets normal manager rights for their own tree. | B.1, B.3, B.4 FR-11, B.9 |
| D-13 | Roles | Keep `User.is_staff` and `is_superuser` in sync with `Employee.is_admin`, and `User.is_active` with `Employee.status`, whenever an Employee is saved. | B.3, B.4 FR-1/FR-2, B.6, B.9, C.4 P1/P3 |
| D-14 | Audit | `AuditLog.actor` becomes nullable, plus a new field `system_actor` (e.g. `"seed_demo"`, `"sync_payroll"`) used when no person is acting. Exactly one of the two must be set. | B.6, B.7, C.4 P2/P8 |
| D-15 | Payroll | "Append-only" means snapshot and hours fields never change after creation. Only `status`, `export_batch`, `exported_at`, `paid_at` and `superseded_at` may change, and only forward: CURRENT → EXPORTED → PAID, and any status → SUPERSEDED. Enforced in code and tested. *Extended by D-118 (SETTLED, `settled_at`) and D-120 (adjustments follow the same rules).* | B.4 FR-11, B.5, B.6, B.9, B.10 |
| D-16 | Tests | New catalogued tests continue as T-43, T-44, … and are added to the B.11 table in the same phase. | B.11, C.4 |
| D-17 | Tests | Every catalogued test's docstring starts with its ID, e.g. `"""T-13: week still open at Saturday 11:59:59."""`. Small helper tests don't need an ID. | B.11 examples |
| D-18 | Data | PROJECT entries must have an active project; all other categories must have no project. | B.6, B.9, C.4 P5 |
| D-19 | Data | Add `Employee.end_date` (nullable, set on deactivation). Entries are allowed only between `hire_date` and `end_date`. Expected hours for a partial week = `expected_weekly_minutes × active weekdays (Mon–Fri) / 5`. Weeks fully outside employment are never "missed". Existing timesheets of a deactivated employee can still be approved and paid. | B.1, B.4 FR-8/FR-11, B.6, B.9, C.4 P5/P8/P9/P11 |
| D-20 | Data | `Employee.email` is the source of truth. `User.email` updates automatically (lower-cased) when HR changes `Employee.email`; both stay unique. | B.4 FR-2, B.6, B.9 |
| D-21 | Timesheet status | Reopen window: `reopen_until` = the later of (unlock/reject time + 48 hours) and the week's normal Saturday 12:00 deadline. When the window ends without resubmission, the week becomes LOCKED. Tested by T-43. | B.4 FR-7/FR-8/FR-9, B.5, B.9, B.11 T-24/T-31/T-43, C.4 P6/P7, D.1 |
| D-22 | Audit | AuditLog actions (full list): CREATE, UPDATE, DELETE, SUBMIT, APPROVE, REJECT, UNLOCK, PUBLISH, SUPERSEDE, EXPORT, PAY, SYNC. Publish, supersede, export, pay and sync each write an audit row. | B.6, B.10, C.4 P8 |
| D-23 | Setup | `createsuperuser` refuses employees whose `is_admin` is off (in addition to unknown, not ACTIVE, or already having an account), so the superuser flags always match the directory (D-13). Set `is_admin` on the employee first. Tested by T-46/T-47. | B.6, C.4 P1 |
| D-24 | Setup | Until Phase 3, `/` is a public static placeholder page that shows no data. Phase 3 puts it behind login; Phase 9 replaces it with the dashboard. | B.8, C.4 P1/P3/P9 |
| D-25 | Setup | `week_start_for`, `deadline_for` and `pay_period_for` are built in Phase 2 (seed_demo needs them), with tests T-12, T-15 and T-16. Phase 5 adds `effective_status`, `expected_minutes_for` and the other calendar tests. | B.9, C.4 P2/P5 |
| D-26 | Setup | Until Phase 11, Django Admin is view-only for every model (passwords shown only as a masked Argon2 summary). Phase 11 adds editing, deactivate and password reset together with their audit rows — ended for directory data by D-87. | B.4 FR-10, C.4 P2/P11 |
| D-27 | Data | Seed history is aligned to pay periods: the 6 completed periods before the current one (26 with `--large`), plus week 1 of the current period when today is in its week 2 — 12 or 13 weeks. The current week is left empty. | B.7, C.4 P2 |
| D-28 | Login | django-axes locks by **account (email)**: 5 failed attempts lock that email for 15 minutes from any computer; `uv run python manage.py axes_reset` clears it (it clears all lockouts; `axes_reset_username <email>` clears just one). The email is trimmed and lower-cased before counting, the 5th failure already shows the locked page, and `axes.W006` (which recommends adding the IP address) is silenced for this reason. | B.4 FR-1, C.4 P3, D.1 |
| D-29 | Login | There is one login page, `/login/`. `/admin/login/` redirects there (keeping `?next=`); a logged-in employee without `is_admin` who opens `/admin/` gets 403. | B.8, C.4 P3/P11 |
| D-30 | Layout | Menu items for pages built in later phases (Timesheets, Requests, Team, Approvals, Payroll) link to simple "coming in a later phase" placeholder pages that already enforce the correct permission on the server, so menus and 403s can be tested from Phase 4. Later phases replace the views but keep the URLs and URL names. | B.8, C.4 P4–P10 |
| D-31 | Roles | Admins see **Team** (everyone) and **Approvals** (their direct reports plus employees with no manager, never themselves), even if they manage nobody. Managers see Team and Approvals for their own reports. Replaces "only for managers" in the C.4 Phase 4 prompt (B.1 row 14, B.3, D-11). | B.1, B.3, C.4 P4/P7/P10 |
| D-32 | Timesheet | Submitting requires at least one entry ("Add at least one entry before submitting"); leave is entered as PTO, Sick or Holiday. | B.4 FR-8, C.4 P5 |
| D-33 | Timesheet | Employees can open only the current week and earlier weeks; future weeks cannot be opened or saved. The current week can be submitted any time before Saturday 12:00, including weekend hours entered in advance (D-09). Future weeks are never counted as missed. | B.4 FR-8, B.8, C.4 P5 |
| D-34 | Timesheet | LOCKED and "missed" are worked out when read (`effective_status`, `week_state`); opening a page never writes. The stored status changes only through actions (save, submit, and later unlock/approve), so a locked week may still be stored as DRAFT. | B.4 FR-8, B.5, B.9 #3, C.4 P5–P7 |
| D-35 | Timesheet | Unlimited rows: **Add row** (HTMX) adds as many rows as needed on any day of the week, and rows of an editable (draft) week can be removed. There is no row limit; the time rules and the 24-hour rule are the only limits. *Since Change 2 the rows are the time slots of the weekly grid (D-106, D-107); there is still no limit.* | B.4 FR-8, C.4 P5 |
| D-36 | Timesheet | Every row has a date, category, project (Project work only, D-18) and a **required reason** (max 255 characters; *the reason is optional since D-128*). `TimeEntry.notes` is renamed to `reason`. | B.4 FR-8, B.6 |
| D-37 | Timesheet | Work rows (Project work, Meetings, Training, Other) and Break rows have a start and end time ("login to logout" for that row) in 15-minute steps; end must be after start and the row cannot cross midnight (latest end 23:45). Hours are calculated from the times and stored as whole minutes. | B.1 row 15, B.4 FR-8, B.6, B.9 |
| D-38 | Timesheet | Rows with times on the same day must not overlap, breaks included; back-to-back rows (end = next start) are fine. | B.4 FR-8, B.9 |
| D-39 | Timesheet | New category **BREAK** ("Break time"): needs start and end times, never a project, and is unpaid — never counted in Hours worked, overtime or payroll. | B.1 rows 15–16, B.4 FR-8, B.6 |
| D-40 | Timesheet | Leave rows (PTO, Sick, Holiday) have hours only, without start or end times. | B.1 row 15, B.4 FR-8, B.6 |
| D-41 | Timesheet | Hours worked = the sum of work rows, excluding Break and leave. Shown per day and per week next to the expected hours, with separate Break and Leave totals and each day's first start and last end time. | B.4 FR-8, B.9 #16 |
| D-42 | Timesheet | The 24-hour limit per day counts work, Break and leave rows together. | B.4 FR-8, B.9, B.11 T-18 |
| D-43 | Timesheet | D-32 stays, and a week containing only Break rows cannot be submitted either. | B.4 FR-8 |
| D-44 | Data | `TimeEntry` gets `start_time`, `end_time` and `reason` (renamed from `notes`) plus the BREAK category in migration `timesheets/0002`. `seed_demo` creates realistic times, reasons and lunch breaks. Existing databases are migrated, never deleted, flushed or reseeded automatically; rebuild them with the D.3 "start over" steps. | B.6, B.7, D.3 |
| D-45 | Payroll | Phase 8 `split_hours` excludes Break from regular hours and overtime. | B.1 row 16, B.9 #12, C.4 P8 |
| D-46 | Change request | A change request can be raised only by the employee, on their own week, when its effective status is SUBMITTED, LOCKED or APPROVED — never DRAFT, NOT_STARTED, REOPENED or future weeks. At most one OPEN request per week (service check + partial unique constraint `one_open_request_per_week`). Raising on a missed week with no timesheet creates that week as LOCKED. | B.4 FR-9, B.6, C.4 P6 |
| D-47 | Change request | Requests are handled by whoever `can_approve` the week's employee: the direct manager, or admins for employees with no manager; nobody handles their own (D-11, D-31). The inbox `/approvals/requests/` (`request_inbox`) is new — Phase 4 had no placeholder for it; `/requests/` (`requests`) lists the employee's own requests. | B.3, B.8, C.4 P6 |
| D-48 | Change request | The handler's note is optional for Reject, Unlock and Edit directly. | B.4 FR-9 |
| D-49 | Change request | **Edit directly** uses the Phase 5b validation for the week's employee (times, reason length — a reason is optional since D-128 —, no overlaps, Break rules, 24 h, employment dates, no Break-only/empty week). The week becomes SUBMITTED (first-time `submitted_at`/`is_late` only if never submitted). If it was in an APPROVED period, `approvals.reset_approval` sets the period to PENDING, its approved weeks to SUBMITTED and calls the payroll hook, in the same transaction (D-10). Audit UPDATE stores before/after status and entries with times and reasons. | B.4 FR-9, B.5, B.9 #10 |
| D-50 | Change request | **Unlock** sets REOPENED with `reopen_until` = the later of now + 48 h and the week's Saturday 12:00 (D-21); an APPROVED week is first reset through `approvals.unlock_week`. An unused window makes the week LOCKED (read-time, D-08, D-34). | B.4 FR-9, B.5 |
| D-51 | Timesheet | A reopened past week stays editable by its employee until `reopen_until`; D-33 only stops future weeks. Employee saves in a REOPENED week write an UPDATE audit row with before/after entries. | B.4 FR-8/FR-9 |
| D-52 | Timesheet | `is_late` is decided by the first submission only: an on-time week reopened and resubmitted stays on time; a missed week submitted later is late and stays late (refines D-08). | B.4 FR-8, B.5 |
| D-53 | Payroll | Payroll hook: `timesheets/services/approvals.py → supersede_payroll_week(timesheet, actor, at)` is called for every week that leaves APPROVED; it does nothing until Phase 8 calls `payroll/services/publish.py → supersede_week` (D-15). | B.9 #10/#13, C.4 P8 |
| D-54 | Approvals | `/approvals/` lists the employees the viewer may approve — direct reports, plus no-manager employees for admins, never the viewer (D-11, D-31) — active employees employed on at least one day of the period, and inactive employees only if they have a timesheet in it (their existing timesheets can still be approved, D-19). Periods are 14 days from `PAY_PERIOD_ANCHOR`; default = the most recent completed period; the picker offers the current period and earlier; `?period=` takes any date and snaps to its period start. | B.4 FR-7, B.8 |
| D-55 | Approvals | Flags: **late** = either week `is_late`; **overtime** = a week's Hours worked (Phase 5b `summarize`, Break excluded) above that week's prorated expected hours; **missing days** = an employed weekday (Mon–Fri, up to today) with no entries at all (leave counts as an entry). | B.4 FR-7 |
| D-56 | Approvals | Only weeks with at least one employed day must be SUBMITTED; a week fully outside employment is not required (refines D-06 for D-19). | B.4 FR-7, B.5 |
| D-57 | Approvals | Reject has the same precondition as Approve and needs a comment; the required weeks become REOPENED with `reopen_until` per D-21 (D-07); the comment is stored on the PeriodApproval and as `manager_note` on the weeks. | B.4 FR-7, B.5 |
| D-58 | Approvals | An open change request on either week blocks Approve and Reject (and bulk approve skips the row) until it is handled. | B.4 FR-7/FR-9 |
| D-59 | Approvals | Unlock on the approvals page reuses Phase 6 `approvals.unlock_week`: it resolves the employee's open request on that week if there is one, otherwise records a manager-authored ChangeRequest (requester = manager, UNLOCKED); a missed week with no timesheet is created as LOCKED first. Audited. | B.4 FR-7, D-06 |
| D-60 | Approvals | Resubmitting a week of a REJECTED period sets the PeriodApproval back to PENDING (`approvals.period_resubmitted`, audited with the employee as actor). | B.4 FR-7, B.5 |
| D-61 | Payroll | Payroll hook `approvals.publish_payroll_period(approval, actor, at)` is called inside the approve transaction; since Phase 8 it only registers the payroll write to run after the main commit (see D-65). | B.9 #13, C.4 P8 |
| D-62 | Data | One PeriodApproval per employee per period: unique constraint `one_approval_per_period` (migration `timesheets/0004`). | B.6 |
| D-63 | Approvals | Bulk approve: only rows with the required weeks SUBMITTED, no flags, no open request and not yet decided can be ticked; the server re-checks every posted row, approves each employee in its own transaction and shows what was approved and what was skipped with reasons. | B.4 FR-7 |
| D-64 | Payroll | **Overtime rule**, per week: worked = Project work + Meetings + Training + Other; regular = min(worked, that week's prorated expected minutes, D-19); overtime = worked − regular; PTO, Sick and Holiday are separate totals, never overtime; Break never counts; total = regular + overtime + PTO + Sick + Holiday. Stored in minutes, shown as hours with 2 decimals. | B.1 row 16, B.9 #12 |
| D-65 | Payroll | **Two databases, fixed order.** The main DB decides first (PeriodApproval is the source of truth). The timesheet hooks only register `transaction.on_commit` callbacks; after the main commit, `publish_period` / `supersede_week` run in their own payroll transaction, then write PUBLISH / SUPERSEDE audit rows. A main rollback never reaches payroll; a payroll failure after the commit leaves the approval in place, rolls back the payroll write completely, is logged, shows an out-of-sync banner on `/payroll/`, and is repaired by `manage.py sync_payroll` (publish every APPROVED period, supersede live records of weeks no longer approved, one SYNC audit row). | B.4 FR-11, B.6, C.4 P8 |
| D-66 | Payroll | A payroll record belongs to one approval decision (`approved_at` = `PeriodApproval.decided_at`): publishing the same decision again is a no-op; a live record from an older decision is superseded and the next version written. Partial unique constraint `one_live_record_per_week` (at most one non-SUPERSEDED record per employee and week). *Extended by D-118: a SETTLED version is the live record of its week.* | B.6, B.9 #13 |
| D-67 | Payroll | Append-only (D-15) enforced in code: `PayrollWeek.save()` refuses changes to frozen fields and any move other than CURRENT→EXPORTED→PAID or →SUPERSEDED, each lifecycle field set once by its own move; `delete()`, `QuerySet.update()`, `bulk_update()` and `QuerySet.delete()` raise AppendOnlyError; the admin is view-only. | B.6, B.10 |
| D-68 | Payroll | Export CSV covers **all CURRENT records of the selected period** (filters only change the view) as one batch numbered `EXP-0001`, `EXP-0002`, …; a batch can be downloaded again without changing anything; every cell starting with `=`, `+`, `-`, `@`, tab or CR gets a leading `'` so Excel/Numbers never run it as a formula. *Extended by D-123: the batch also holds the period's adjustments; hour columns are app-made numbers written as is, text cells stay formula-safe.* *Since D-135 only Finalize & export creates a batch, one per register.* | B.4 FR-11 |
| D-69 | Payroll | Mark as paid works per batch: its EXPORTED records become PAID (`paid_at`); anything else in the batch (e.g. superseded) is untouched. *Extended by D-123: adjustments in the batch are paid too.* | B.4 FR-11 |
| D-70 | Payroll | Corrections = SUPERSEDED records that had been exported or paid, shown with their replacement version (or "waiting for re-approval") and the difference in hours. *Replaced by D-124 (Corrections with adjustments).* | B.4 FR-11 |
| D-71 | Payroll | The snapshot's `expected_weekly_minutes` is that week's prorated expected minutes (D-19). Deactivated employees' approved weeks are published, exported and paid like anyone else's. | B.6, B.4 FR-11 |
| D-72 | Ops | `backup_db` copies both databases with SQLite's online backup API through a separate read-only connection (safe while the app runs) to `backups/db-YYYYmmdd-HHMMSS.sqlite3` and `backups/payroll-…` with the same timestamp; `--dir` chooses another folder. | D.2, D.3 |
| D-73 | Data | `seed_demo` fills payroll after the main seed commits (publish every approved period; oldest periods EXPORTED and PAID, next EXPORTED, newest CURRENT; one correction). If the payroll part fails, the main data stays and `sync_payroll` completes it; seed_demo still refuses when data exists. | B.7 |
| D-74 | Analytics | Dashboard range = the last N weeks ending with the current week (N = 4, 12 or 26; default 12; anything else → 12). The current week shows in the hours chart but counts for on-time / late / missed only after its Saturday 12:00 deadline. | B.4 FR-5 |
| D-75 | Analytics | A week counts when its deadline has passed and the person was employed on at least one weekday of it (D-19). **On time** = submitted, first submission on time (`is_late` False, D-52); **late** = submitted with `is_late`; **missed** = never submitted (no timesheet or no `submitted_at`). On-time rate = on time ÷ (on time + late + missed). `week_state().is_missed` uses the same rule, so `/timesheets/` and the dashboard agree: a re-locked week counts by its first submission; a missed week reopened but not yet resubmitted stays missed. | B.4 FR-5/FR-8, B.9 #3, #15 |
| D-76 | Analytics | Dashboard overtime = payroll `split_hours` per week (prorated expected) summed over SUBMITTED and APPROVED weeks in the range, so approved weeks match the payroll records exactly. | B.4 FR-5 |
| D-77 | Analytics | The hours charts use every saved entry in the range (drafts and the current week included): Hours worked = work rows; by project = Project work rows; by category = work categories plus leave; Break is listed separately as unpaid and excluded from every total. | B.4 FR-5 |
| D-78 | Analytics | Approval outcomes: every pay period overlapping the range in which the person was employed, with its PeriodApproval status (no record = pending); the current, unfinished period is shown as "in progress" and not counted. | B.4 FR-5 |
| D-79 | Analytics | The dashboard is built by `analytics/services/metrics.py → dashboard_for(employee, weeks, now)` and rendered by `templates/analytics/_dashboard.html` plus `parts/*.html`, which take that object (and `own`) — Phase 10 reuses them read-only for a team member. | C.4 P9/P10 |
| D-80 | Analytics | Charts use the vendored Chart.js with data only through `json_script`; every chart has a table or text with the same numbers; friendly empty states. Viewing never writes (D-34) and uses a fixed number of queries whatever the range. | B.4 FR-5, B.10 |
| D-81 | Team | Who is on `/team/`: **whole tree** = the viewer's reporting tree, or **everyone** for an admin; **direct reports** = only people whose manager is the viewer. The viewer is never listed; the payroll flag adds nothing (D-12). An optional team filter narrows the list (an unknown value = all teams). People with no employed day in the range are left out; inactive employees appear only with a timesheet in the range (as D-54). | B.4 FR-6, B.3 |
| D-82 | Team | **Utilization** = hours worked ÷ available hours, where available = prorated expected (D-19) − leave hours, summed over weeks in the range whose deadline has passed (the current week is not counted). Break never counts. "—" when nothing is available. Team average = total worked ÷ total available (weighted by available hours, not a mean of percentages). | B.4 FR-6 |
| D-83 | Team | **This week's compliance** lists everyone selected who is employed in the current week and hasn't submitted it (not SUBMITTED/APPROVED): "Not submitted yet" before Saturday 12:00, then "Missed" (never submitted, D-75), or "Reopened"/"Locked" for a week reopened after a submission. | B.4 FR-6 |
| D-84 | Team | Per-employee table: hours worked (all weeks, D-77), utilization (D-82), on-time rate, late and missed weeks (Phase 9 `punctuality`, D-75), overtime (Phase 9 `overtime` = payroll split, D-76), and **pending approvals** = finished pay periods in the range still PENDING (Phase 9 `approval_outcomes`, D-78). Sorted on the server with `?sort=<column>&dir=asc|desc`, ties by name; unknown columns sort by name. | B.4 FR-6 |
| D-85 | Team | **Drill-down is read-only.** `/team/<code>/` reuses `_dashboard.html` with `own=False` (no "Open this week") plus that person's timesheets list; each week opens `/team/<code>/weeks/<YYYY-MM-DD>/`, which shows the rows, day summary and status with no edit, submit or approve controls (those stay on `/approvals/` and change requests). Access = `can_access_team` + `can_view` (403 otherwise; unknown code 404); a viewer may open their own drill-down. | B.8, D-30 |
| D-86 | Team | **Performance.** The reporting tree is built in memory from one `(id, manager_id)` query (cycle-safe; T-27/T-28 unchanged). The team page and dashboard load people, timesheets, entries (as light read-only `EntryFacts` records via `values_list`, not model objects), projects and approvals in a fixed number of queries, whatever the tree size or range (T-132); measured in the test DB with ~500 people and 26 weeks of entries: CEO 0.3 s (12 weeks) / 0.6 s (26 weeks). `uv run python manage.py time_team_page <email> [--weeks 4|12|26] [--direct]` renders `/team/` in memory (no session, no writes) and prints the time and query count. | B.9 #6, B.10 |
| D-87 | Admin | **D-26 ends for directory data only.** Editable in Admin: **Employee** (first/last name, job title, location, email, team, manager, hire date, expected weekly hours typed as hours and stored as minutes, is_admin, is_payroll; new employees can be added), **Team** (name, department; add), **Project** (name, active; code only when adding). Not in the employee form: `employee_code` after creation, `status` and `end_date` (Deactivate/Reactivate only). Read-only: Timesheet, TimeEntry, PeriodApproval, ChangeRequest, AuditLog, PayrollWeek, User (masked password) and the django-axes records; Django's `Group` is unregistered (access comes from is_admin, D-13). **Nothing can be deleted in Admin** (no delete permission, no "delete selected"); retire a project by clearing Active, an employee by deactivating. A changed expected weekly hours value applies to every week computed afterwards (no per-week history). | B.4 FR-10 |
| D-88 | Admin | Every Admin add/change goes through `directory/services/directory_admin.py` (`save_employee`, `save_team`, `save_project`; actions call `deactivate`, `reactivate`, `reset_password`, `export_employees`), which checks the rules, saves and writes the CREATE/UPDATE audit row with the admin as actor in one transaction; before/after hold only the changed fields and a save with no changes writes nothing. Audit `entity_id` as before: employee code, team name (before a rename), project code. | B.10, CLAUDE.md |
| D-89 | Admin | Directory safety rules (`check_employee`, and the same checks in the CSV import): nobody is their own manager; a manager change that makes a reporting loop is refused; a newly assigned manager must be ACTIVE; you cannot remove your own admin flag; at least one ACTIVE admin always remains; a new or changed email is lower-cased, unique across Employee and User (any case) and must end in `COMPANY_EMAIL_DOMAIN`; a changed hire date may not be after the person's first saved entry or after their end date. The command-line import and `seed_demo` keep the Phase 2 rules plus the loop and last-admin checks; the domain and "your own" rules apply when an admin imports. | B.4 FR-10, B.9 |
| D-90 | Admin | **Deactivate** (admin action with a confirmation page; all or nothing for the selection): status INACTIVE and `end_date` (default today; allowed from the hire date and the last saved entry up to today, never in the future). The User becomes inactive (D-13), so an open session ends on the next request; history stays and existing timesheets can still be approved and paid (D-19). Refused for yourself, for someone who still manages ACTIVE people outside the selection ("reassign their reports first"), and when no ACTIVE admin would remain. **Reactivate**: ACTIVE with `end_date` cleared, hire date unchanged. Both write an UPDATE audit row. | B.4 FR-10, D-19 |
| D-91 | Admin | **Password reset by HR** from the employee's admin page: a temporary password typed twice that passes `AUTH_PASSWORD_VALIDATORS`; Argon2 hash stored and `User.must_change_password` set (migration `directory/0002`). The person's other sessions end (session hash), their axes lockout is cleared, and the UPDATE audit row holds only `{"changed": ["password"], "must_change_password": true, "lockout_cleared": n}`. While the flag is set every page except Profile, logout and static files redirects to Profile; the profile password change clears it. Not for yourself (use Profile) or people without an account. `/admin/password_change/` redirects to Profile so every change is audited. Passwords are never shown. | B.4 FR-2/FR-10, B.6 |
| D-92 | Admin | **Employee CSV in Admin** (own views; django-import-export would bypass `import_employees` and the audit log, and was removed in Phase 12, D-98). Import: upload (≤ 1 MB, UTF-8) → `import_employees(..., actor=admin, dry_run=True)` (same code, rolled back) → every error with its line, or a summary of created/updated (with changed fields)/unchanged/new teams → **Confirm** re-runs it for real on exactly that file (signed, valid 1 hour); all or nothing; audited with the admin as actor. Export (current list filters): the import columns plus `end_date`, formula-safe via payroll `safe_cell` (D-68) — the importer strips that leading `'` again, so an exported file re-imports with no changes; an EXPORT audit row records the row count. | B.4 FR-10, B.7 |
| D-93 | Admin | **Admin access**: a custom default admin site admits only logged-in ACTIVE employees with is_admin; anyone else logged in gets 403 straight away, anonymous users go to `/login/` (refines D-29). Search and filters: employees by name, code, email, job title, team, department and manager name, filtered by status, team, department, is_admin, is_payroll and manager (managers only); teams by name/department; projects by code/name/active; timesheets by status, week, team and employee; AuditLog by action, entity type, actor, system actor and date (plus date hierarchy). | B.4 FR-10, B.8 |
| D-94 | Tests | **E2E tests** live in `tests/e2e/`, marked `e2e`, and run against pytest-django's `live_server` on the **test databases** (both, `transaction=True`) — never `db.sqlite3` or `payroll.sqlite3`. Data comes from factories in each test (not `seed_demo`). The clock is fixed with `time_machine` at Wed 2026-10-21 10:00 Chicago (`tick=True`) and moved with `move_to()` for deadline tests. Only Playwright `expect(...)` and explicit waits, never sleeps. One browser context per person; confirm dialogs are accepted. `DJANGO_ALLOW_ASYNC_UNSAFE=true` is set for e2e only (Playwright's sync API runs an event loop in the test thread). Catalogued as T-146–T-155. | B.11, C.4 P12 |
| D-95 | Tests | **E2E is mandatory**: `test_all.sh` step 5 runs `uv run pytest -m e2e` and fails on any non-zero exit code, including 5 ("no tests collected"); this ends the D-01 skip rule. Chromium is installed once by the owner (`uv run playwright install chromium`). Extra script arguments are passed to this step (e.g. `--browser-channel chrome`). | B.11, D-01 |
| D-96 | Hardening | **DEBUG off for daily use**: `.env.example` has `DJANGO_DEBUG=False`. With DEBUG off the vendored `/static/` files are served by a URL rule using `django.contrib.staticfiles.views.serve(insecure=True)` (open to anonymous users so the login page has its CSS) — acceptable for a local single-machine app with no build step and no extra package. Friendly `404.html` (site layout) and `500.html` (plain HTML, no context or database) never show code or settings. DEBUG=True still works for development. | B.10, D.2 |
| D-97 | Hardening | `manage.py check --deploy` **HTTPS-only warnings do not apply**: W004 (HSTS), W008 (SSL redirect), W012 (`SESSION_COOKIE_SECURE`), W016 (`CSRF_COOKIE_SECURE`). The app is served over plain HTTP on `127.0.0.1` (or a trusted office network, D.2): secure-only cookies would never be sent, so nobody could log in, and HSTS would force browsers onto HTTPS for the host. They are documented, not silenced, so they show up again if the app ever moves to a server — then set them. Every other deploy check passes once `.env` has `DJANGO_DEBUG=False` and a long random secret key. | B.10, D.2 |
| D-98 | Setup | **django-import-export removed** (`uv remove django-import-export`, also dropping `tablib` and `diff-match-patch`); nothing used it — the admin CSV import/export are our own audited views (D-92). Removed from CLAUDE.md, B.2 and the Phase 1 prompt. | B.2, C.2, D-92 |
| D-99 | Scope | **Known limitations of version 1**: one Mac, SQLite and plain HTTP (not for internet exposure); no notifications or email, so no "forgot password" — HR resets passwords (D-91); no holiday calendar or delegated approvals; one company time zone for every deadline; payroll CSV in the app's own format; a changed expected weekly hours value has no per-week history (D-87). See D.5 for what comes next. | README, D.5 |
| D-100 | UI | **Change 1 – Modern UI: one theme stylesheet.** `static/css/theme.css`, loaded after the vendored Bootstrap 5.3.8 on every page (no CDN, no build step, no new package, no downloaded fonts). Design tokens as CSS variables (`--ts-*`): one accent `#2563eb`, slate neutral greys, status tones, spacing 4/8/12/16/24/32 px, radii 6/10/14 px, two soft shadows, 150 ms transitions; mapped onto Bootstrap's variables (`--bs-primary`, body font and colours, button, alert and focus-ring variables) so existing classes follow. System font stack `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`; tables use tabular figures with numbers right-aligned. One visible 3 px accent focus ring for keyboard users; `prefers-reduced-motion` switches transitions off. Text and badges meet WCAG AA (T-159). Behaviour, URLs, permissions, rules and the labels tests rely on are unchanged. | B.8, B.10 |
| D-101 | UI | **Layout.** Light top bar with a 1 px bottom border: active page as a tinted pill (`aria-current="page"`), pill badges, and a user block with an initials avatar, name · Employee ID and title · team; Log out stays a POST button. Pages: a page header (title, short subtitle, actions on the right), content in cards, max width 1200 px (1400 px for Team, Approvals and Payroll). Tables: soft header, row hover, comfortable rows; long tables (timesheets list, approvals, team, payroll) keep their header visible in a 70vh scroll box on laptop screens; on narrow windows tables scroll sideways inside their card and the page itself never does. Login, sign-up, profile, account locked, 403, 404 and 500 are centered cards with the app name (500 stays standalone HTML with the token values inline, D-96). | B.8 |
| D-102 | UI | **One status badge component**, `templates/includes/status_badge.html` (context: `status`, optional `label` and `badge_id`; included with `only`), plus `includes/week_badges.html` (a week's status with its Late / Missed / Change requested flags) and `timesheets/_flags.html` (approval flags). Every page that shows a week, pay period, change request or payroll status uses them. The `status_tone` filter (replacing `status_badge`) maps codes to tones: neutral (Not started, Not employed, Pending, In progress, Current, Superseded, Read-only, Not submitted yet), draft (grey), submitted (blue; also Exported), approved (green; also Paid, Unlocked, Edited), danger (red; Locked, Missed, Rejected, Missing days), reopened (violet), warning (amber; Late, Change requested, an open change request), info (cyan; Overtime). Soft background with dark text, always with the word, never colour alone. | B.5, B.8 |
| D-103 | UI | **Charts use the tokens**: `dashboard.js` and `team.js` read `--ts-chart-series` (the accent `#2563eb`, which passes the palette validator against the light surface), `--ts-chart-muted` and `--ts-chart-grid` with `getComputedStyle`, falling back to the same values. Every chart keeps its table or text version (D-80). | B.4 FR-5/FR-6 |
| D-104 | UI | **Django Admin: light branding only.** `site_header`/`site_title` = "Timesheets Admin"; `templates/admin/base_site.html` sets the admin's own colour variables (primary, header, breadcrumbs) to the accent and slate tokens in light mode and makes the site name dark. The admin's pages and dark mode are not restyled. | B.4 FR-10 |
| D-105 | UI | **Visual review tool** (not part of `test_all.sh`): `SCREENSHOTS_DIR=<folder outside the repo> uv run pytest scripts/visual_review --browser-channel chrome`. It starts a live test server on the **test databases**, runs `seed_demo` there with a fixed clock (Wed 2026-10-21 10:00, also in the browser), logs in as dev1, eng.manager, payroll and hr, checks each page's status code and that the page never scrolls sideways, and saves full-page screenshots at 1440×900 and 390×844. It never touches `db.sqlite3` or `payroll.sqlite3`. | B.11 |
| D-106 | Grid | **Change 2 – Weekly grid.** The week's entries are shown as a grid instead of a list: one row per Project / Category (project rows by code as "PRJ-001 Customer Portal / Project work", then Meetings, Training, Other, "Break (unpaid)", then PTO, Sick, Holiday tagged "leave"); columns Mon–Sun headed with the day and date ("Mon" / "Oct 26, 2026"), then **Total worked hours**; a footer with Total worked hours per day and for the week. The footer counts work rows only; Break and leave rows show their own totals and are never added to it — exactly as `summarize` (D-39, D-41). The day summary (first start, last end, hours worked, expected, break, leave) stays below the grid. Week, deadline and pay periods are unchanged. *Column order superseded by D-111: the columns run Sun–Sat since Change 3.* | B.4 FR-8, B.8 |
| D-107 | Grid | **Cells and slots.** A cell is a button showing its hours (2 decimals) and opens a dialog for that row and day: work and Break cells hold one or more time slots (start, end, reason; "+ Add time slot", Remove; *"+ Add another time slot" since D-127*); leave cells hold hours and a reason (*optional since D-128*). Each slot is posted as one entry with the same `entry-N-*` fields as before (day, category and project fixed by its cell), so `parse_entries`, `validate_entries`, `save_week`, `edit_directly`, audit and approval/payroll hooks are reused unchanged; no model change, no migration. Slots left empty are dropped before posting; the server still ignores blank entries. "+ Add row" (HTMX, `timesheet_row`) offers a category and, for Project work, an active project (D-18); duplicates are refused (*superseded by D-127: "+ Add row" for an existing row points at it instead of showing an error*); a row added without slots survives a failed save (`grid-row` keys) and disappears after a successful one. *Since D-129 / D-130 a whole row can also be moved to another project or category, or deleted, from its "⋮" menu.* | B.4 FR-8, D-35 |
| D-108 | Grid | **Errors on the right cell.** Messages are unchanged. Reading problems (`ParsedEntries.problems`) go to the slot's cell; rule messages go to every cell whose entry they name, matched with `validation.mentions(entry)` (the same "Tue 20 Oct, PRJ-001 09:00–12:00" texts the messages are built from); an overlap marks both cells; the 24-hour rule marks the day's footer total; anything else (e.g. an empty week) is listed at the top. Marked cells are outlined with `aria-invalid`, list their messages inside the dialog, and the summary at the top links to them. | B.9 #9 |
| D-109 | Grid | **One grid component**: `templates/timesheets/_grid.html` (+ `_grid_row.html`, `_grid_slot.html`) built by `timesheets/grid.py → build_grid`. Editable on the employee's week page and on Edit directly (same rules and audit as before); read-only on submitted, approved and locked weeks, the change-request detail, both weeks of the approval page and the Team week view, where a cell's dialog lists its slots' times, hours and reasons without inputs. It replaces `_row.html` and `timesheet.js`. | B.8, D-85 |
| D-110 | Grid | **Comfort and accessibility**: live cell, row and footer totals while typing (convenience; the server recomputes, and the HTMX day summary still updates); the browser asks before leaving with unsaved changes (never after Save/Submit); cells are buttons with descriptive names ("PRJ-001 Customer Portal / Project work, Mon Oct 26: 8.00 hours, 2 slots"; since D-127 followed by the slot times, and the cell shows "8.00 · 2 slots"); native `<dialog>`: focus moves in, Esc closes, focus returns to the cell; Enter inside a slot doesn't submit the week. On narrow windows the grid scrolls sideways with the first column fixed; the page itself never scrolls sideways. Vendored HTMX and plain JavaScript only (`static/js/grid.js`). | B.10 |
| D-111 | Calendar | **Change 3 – weeks run Sunday → Saturday** and are identified by their Sunday; `Timesheet.week_start` is always a Sunday. The rule lives only in `timesheets/services/calendar.py` (`WEEK_START_WEEKDAY = 6`, `week_start_for`, `week_days` Sun…Sat); every page and service (timesheet list and week, grid and day summary columns, countdown, change requests, approvals and the pay-period picker, payroll labels/filters/CSV, dashboard, team analytics, seed) uses it. **Supersedes** B.1 row 9 (Monday → Sunday) and the column order of D-106. | B.1 row 9, B.9 #1, FR-8 |
| D-112 | Calendar | The deadline stays **Saturday 12:00 noon company time**, now the **last day** of the week (`DEADLINE_DAY_OFFSET = 6`). D-09 still applies (the rest of Saturday may be entered in advance). LOCKED/missed, late (D-08, D-52), the reopen window (D-21: later of +48 h and that week's Saturday 12:00) and "missed = never submitted" (D-75) are unchanged. | B.1 row 10, B.5, FR-8 |
| D-113 | Calendar | **Pay periods**: 14 days anchored on **Sunday 2026-01-04** (`PAY_PERIOD_ANCHOR`, settings default and `.env.example`). The anchor must be a Sunday: system check `timesheets.E001` makes `runserver`, `migrate`, `seed_demo` and every management command refuse to start with "PAY_PERIOD_ANCHOR … is a Monday; it must be a Sunday …", and `pay_period_for` raises `ValueError` for a non-Sunday anchor. Tests set the anchor themselves (`tests/conftest.py`), whatever `.env` says. **Supersedes** B.1 row 12 (Monday 2026-01-05). | B.1 row 12, FR-7 |
| D-114 | Calendar | **Working days stay Monday–Friday** (D-19): `working_days(week_start)` = Mon…Fri (the week's days 2–6), used by expected hours and partial weeks, the day summary's expected column (and so the missing-day flag, D-55) and the seed. Sunday and Saturday are the weekend at the two ends of the week. | B.9 #5, D-19 |
| D-115 | Calendar | **Week links use the Sunday.** Any other date in `/timesheets/<date>/` (e.g. an old Monday link) or the Team week view redirects to the week that contains it; future weeks stay 404 (D-33). HTMX endpoints (day summary, add row) accept any date of the week. | B.8 |
| D-116 | Calendar | **Daylight saving**: the US change on Sunday 2026-11-01 (and 2026-03-08) now falls on the first day of a week. Deadlines are built with `zoneinfo`, so Saturday 12:00 stays local either side; time entries remain wall-clock times as before (D-37). | B.9 #2, T-15 |
| D-117 | Data | **No data conversion**: there is no data migration and no schema change (`week_start` stays a date; comments only). Existing Monday-week databases must be rebuilt by the owner (D.3 "Start over"). `seed_demo` creates Sunday weeks, history aligned to whole pay periods (D-27) with the current week empty, and the same scenarios (dev1/dev2 period pending, one rejected period, one open change request, one manager edit, exported/paid batches and one correction); decisions stay on Mondays, exports on Fridays and recent hires on Wednesdays. | B.7, D-27, D.3 |
| D-118 | Payroll | **Change 4 – settled weeks.** `PayrollWeek` gains status **SETTLED** ("a corrected version paid through the original payment plus adjustments; never exported as a week row") and lifecycle field `settled_at`. New moves: CURRENT → SETTLED, SETTLED → SUPERSEDED; new records still start CURRENT; a SETTLED record is the week's live record (D-66). Rule: once any version of an employee-week has been exported (`exported_at` set), every later version is settled as it is published. | B.4 FR-11, B.5, D-15 |
| D-119 | Payroll | **Adjustment = new version − previous version** of the week, separately for regular, overtime, PTO, sick, holiday and total minutes (signed). The previous version is the exported/paid one or an earlier settled one, so a week's adjustments always add up to "latest version − version first paid" and nothing is counted twice, also when an earlier adjustment has not been exported yet. A zero difference settles the week without an adjustment. Weeks whose earlier versions were never exported keep the old behaviour (new version CURRENT, exported normally). | B.4 FR-11 |
| D-120 | Payroll | **`PayrollAdjustment`** (payroll database only, append-only like D-15 through the shared `AppendOnlyRecord` base): frozen employee snapshot, the corrected week and its period, the period it is carried to, old and new version, the six signed amounts, approver and approval time, reason and source timesheet id; status CURRENT → EXPORTED → PAID with `export_batch`, `exported_at`, `paid_at`; one per (employee, week, new version). Schema migration `payroll/0002` (payroll database only). | B.6, D-15, D-67 |
| D-121 | Payroll | **Carry-forward period**: from the later of (the period after the corrected week's own period) and (the most recent completed period at re-approval, `default_period(at)`), the first period — stepping 14 days — that has no export batch yet (no exported week record or adjustment). That period's next export includes the adjustment. *Since D-136 a period also counts as exported when its register is finalized.* | B.4 FR-11 |
| D-122 | Payroll | **Reason** = the reason of the latest handled change request (Edit directly or Unlock, including the manager-authored unlock from Approvals) on the week's timesheet, otherwise "Re-approved after a change". Stored on the adjustment and shown **only on the Corrections page** — never in the CSV, on the Payroll page or in the audit summary (D-12). | B.4 FR-11, D-12 |
| D-123 | Payroll | **Export, CSV, Mark as paid**: Export CSV takes the period's CURRENT week records and CURRENT adjustments into one batch (shared `EXP-` numbering); SETTLED weeks are never exported. CSV columns: `batch, employee_code, row_type (WEEK/ADJUSTMENT), …, week_start` (blank for adjustments), `original_week` (adjustments), hours, `version` (`1→2` for adjustments), `status`; per employee, week rows first. Hour columns are numbers the app computes and are written as is (adjustments may be `-1.50`); every text cell still goes through `safe_cell` (D-68). Mark as paid pays the batch's records and adjustments. *The detailed CSV is unchanged; since D-135 it is downloaded per register.* | B.4 FR-11, D-68, D-69 |
| D-124 | Payroll | **Pages**: Payroll totals keep the week columns (each week's current approved hours, settled weeks included), add **Adjustments** (carried into this period) and **Total = weeks + adjustments**; a table "Adjustments carried to this period" (same filters); the period list includes periods with only adjustments; the export button counts both. **Corrections** (replaces D-70): one row per version change of a week that had been exported or settled — old version (Paid/Exported with batch, or Settled), new version, difference, the adjustment with its period and status (**Scheduled**, **Exported in EXP-xxxx**, **Paid**), the reason; "waiting for re-approval" before re-approval and "no adjustment (0.00)" for a zero difference. *Follow-up:* in a period's week records, each Settled week shows "Settled by adjustment in <period>" linking to the period its adjustment was carried to, or "No difference to pay" for a zero difference (T-182). *Replaced by D-138 (pay period list and register page).* | B.4 FR-11, B.8 |
| D-125 | Payroll | **Audit and sync**: adjustments are created in the same after-commit payroll transaction as the settled version (D-65). Audit reuses existing actions (no change to `AuditLog.Action` or the main database): **PUBLISH** with entity `PayrollAdjustment` (approver or system actor; versions, amounts, period; no reason); the batch **EXPORT**/**PAY** rows add `adjustments` when the batch has any. `sync_payroll` also settles live CURRENT versions of once-exported weeks and creates missing adjustments, idempotently; its SYNC row reports `adjustments`; `sync_payroll()` still returns (published, superseded). | B.9 #13, D-22, D-65 |
| D-126 | Data | **Seed**: the existing correction (an hour added to a paid week of the oldest period) now publishes its v2 as SETTLED with a **+1.00 h adjustment, Scheduled**, carried to the first period without an export batch (the last approved period, whose weeks are still waiting to be exported) — one correction plus one carried-forward adjustment. | B.7, T-114 |
| D-127 | Grid | **Change 5 – Easier multiple time slots** (refines D-107 and D-110). Still **one row per Project / Category**; a second period of work on the same day is another time slot in the same cell. **"+ Add row" for a row that is already there** shows no error: the dialog closes, the existing row is scrolled into view and highlighted briefly (no animation with reduced motion), its first day cell gets focus, and a notice under the grid (`role="status"`) says "PRJ-001 Customer Portal / Project work already has a row. Click a day to add another time slot (for example 2:00 PM – 5:00 PM)." (leave rows: "PTO already has a row. Click a day to enter or change its hours."). **Cell dialog:** the button reads "+ Add another time slot" (leave: "+ Add another leave entry"); a work or Break cell that already has slots opens with them listed plus one empty new slot, focused and ready to fill; a leave cell opens as before. An offered slot left empty is dropped when the dialog closes and never posted (as before). **Hint:** a cell with more than one slot shows "8.00 · 2 slots"; its tooltip (`title`) and accessible name list the slot times ("08:00–13:00, 14:00–17:00"; leave: hours) — rendered on the server (`Cell.slot_times`), kept up to date while typing, and shown on read-only grids too (submitted weeks, change requests, approvals, Team week view) as well as on Edit directly. **Rules unchanged:** 15-minute steps, no overlaps across all rows of a day, a reason on every slot (*optional since D-128*), Break never counted; the server's validation stays the authority. | B.4 FR-8, B.10 |
| D-128 | Timesheet | **Change 6 – Optional reason on time entries** (supersedes the "required reason" of D-36 and the reason rule in D-49, D-107, D-127 and B.4 FR-8). The Reason field stays in every time-slot dialog (employee grid and Edit directly) but may be left empty for work, Break and leave; an empty or spaces-only reason is saved as blank (`""`); at most 255 characters is still checked. Read-only cell dialogs (submitted, locked and approved weeks, change requests, approvals, Team week view) show the Reason column only when at least one of the cell's slots has a reason; a slot without one shows an empty cell there. All other entry rules are unchanged; an entry with nothing typed is still ignored and one with only a reason still needs its times or hours. **Still required:** a change request's reason ("Explain what needs to change.") and a rejection comment (D-07). `TimeEntry.reason` gets `blank=True` in migration `timesheets/0005` (no database column changes). The demo data still gives every row a reason. | B.4 FR-8, B.6 |
| D-129 | Grid | **Change 7 – Row actions.** On an **editable** grid only — the employee's own open week (Draft, Reopened after an unlock or a rejection) and the manager's Edit directly — each row's label has a Bootstrap "⋮" dropdown (`aria-label="Row actions for PRJ-001 Customer Portal"`) with **Change project / category** and **Delete row**; the menu opens below ⋮, aligned to its start, on top of everything in the table and never clipped (Popper `fixed` strategy, so the scrolling table and the rounded card can't clip it; the open menu's sticky name cell is raised above the other rows' sticky cells). Both open in the grid's native dialog, like "+ Add row" and the cells (never a browser `confirm()`); Esc or Cancel closes it and focus returns to ⋮. Delete asks first: "Delete PRJ-001 Customer Portal? This removes 3 time slots (6.50 h) from this week." (leave: "leave entries"), counted from the grid as typed; a row without slots is removed at once. The action POSTs the whole week **as typed** (HTMX, CSRF) to `timesheet_rows` / `request_rows`; the server applies it with `timesheets/services/grid_rows.py` and returns the re-drawn grid (row, day and week totals) with a status notice ("…Save to keep this change."); the day summary refreshes. **Nothing is saved until the week is saved** (Save draft / Submit through `save_week`, "Save and submit for the employee" through `edit_directly`), so every entry rule, status-on-read, the single Edit directly UPDATE audit row (before/after) and re-approval → publish → pay adjustments (D-118) are unchanged; leaving without saving warns as usual (D-110). **Server checks:** POST only; the employee's endpoint refuses a week that isn't editable (403, `WeekLocked`); Edit directly's needs an open change request the user may handle (403, D-47). Submitted, approved, exported and paid weeks stay read-only, with no menu; they change only through a change request. | B.4 FR-8, B.10, D-49 |
| D-130 | Grid | **Change 7 – Row action rules** (one place: `grid_rows.py`). **Change project / category** moves every slot of the row to the chosen category (and active project for Project work, D-18; the same check as "+ Add row"); dates, times, hours and reasons are kept. Allowed: a work or Break row → any work category or Break (the dialog warns "Break is unpaid: these hours will no longer count as worked time", or that Break hours will count as worked time); a leave row → another leave type only, because leave has hours, not times. Anything else is refused (400) and nothing changes. If the chosen project / category **already has a row this week, the slots merge into it**; the dialog says so first ("… already has a row this week: the 3 time slots of this row will be added to it.") and the notice confirms it; overlaps and all other rules are checked as always when the week is saved (D-38). **Delete row** removes the row's slots for this week only. No schema change. | B.4 FR-8 |
| D-131 | Hardening | **Static files are revalidated on every page load.** `/static/` (D-96) answers with `Cache-Control: no-cache`; an unchanged file answers `304 Not Modified` to the browser's If-Modified-Since, so this costs almost nothing. Reason: before, files were served with only Last-Modified, so Chrome reused cached copies by its own heuristic (about a tenth of the file's age); after an update a page could run with the previous `grid.js` and `theme.css` — found in Change 7, where the new ⋮ menu then sat under the next row and its items did nothing. Chosen over versioned file names (`ManifestStaticFilesStorage` needs `collectstatic`, which this app doesn't use) and a hand-bumped `?v=` (easy to forget). After this change, one hard reload (⌘⇧R) clears copies a browser cached earlier. | B.10, D-96 |
| D-132 | Payroll | **Change 8 – Pay Period Register.** Every ended 2-week pay period has a register. While it isn't finalized it is **worked out live** (status **OPEN**, then **READY**) — never saved, because an approval can still go back to PENDING when an approved week is edited or unlocked, and payroll records only move forward. **Finalize & export** saves it as `PayrollRegister` (payroll database only, append-only through `AppendOnlyRecord`: born **FINALIZED** with its batch, who finalized it and when, why it was ready, approved x of y; the only move is FINALIZED → **PAID**, setting `paid_at`) with one `PayrollRegisterLine` per employee (`FrozenRecord`: saved once, never changed or deleted; a foreign key to its register inside the payroll database, none across databases). Migration `payroll/0003`; no change to `db.sqlite3`. | B.4 FR-11, B.6, D-15 |
| D-133 | Payroll | **Approval deadline and READY.** New settings `APPROVAL_DEADLINE_DAYS` (default 2) and `APPROVAL_DEADLINE_TIME` (default 12:00): managers approve a period by that many days after its last day (Saturday), company time — Monday 12:00 by default. The Approvals page shows "Approve by …" and an **Overdue** badge on rows not approved after it. A register is **READY** when the period has ended, payroll is in sync for it (every approved week has its record, D-65), and either everyone who must be approved is approved with no open change request on the period's weeks, or the deadline has passed. Before that "Finalize & export" is disabled and refused on the server — no early finalize. | B.4 FR-7, FR-11 |
| D-134 | Payroll | **Register lines.** One line for each person who must be approved in the period — the approvals rule (D-54), now one shared function `must_be_approved`, company-wide — and one for anyone else with something to pay. Columns: code, name, department, team, approver and approval time; Week 1 and Week 2 regular, overtime, PTO, sick, holiday; Period (their sums) and Period total; Carry-forward in (regular, overtime, PTO, sick, holiday, Carry total, signed) and the original weeks they came from; **Pay total = Period total + Carry total**; a totals row on screen. Every number comes from PayrollWeek and PayrollAdjustment records (`split_hours`, so Break is never paid); nothing is worked out a second way. **Line status:** Approved; **Missed – not submitted** (a required week not submitted) or **Waiting for manager approval** (submitted, not approved) — both 0.00, read from the approvals data, timesheets never changed; **Carry-forward only**. The page lists the people still pending with their approver (manager, or "HR / an admin") and why. | B.4 FR-11, D-12, D-54 |
| D-135 | Payroll | **Finalize & export, Mark as paid, downloads.** Finalize & export (READY only) runs in one payroll transaction: builds the lines, takes **one** new batch number (`EXP-`, also counting register batches), moves exactly the records the lines pay to EXPORTED in it, saves the register and lines; EXPORT audit row (entity `PayrollRegister`). It can't run twice for a period and never picks up an exported record again. **Mark as paid** moves the register and its batch's records to PAID once (PAY audit row). The old "Export CSV any time" button and the per-batch Mark as paid are **removed** — Finalize & export is the only action that creates a batch (`export_period` stays as an internal helper to build older-style data in tests). Finalized registers can be downloaded any number of times without changing anything: **Register CSV** `payroll-register_<start>_to_<end>_<batch>.csv` (the register columns, line status and carry_from; no totals row) and **Detailed CSV** `payroll-detail_…` (the WEEK / ADJUSTMENT format of D-123, unchanged); **Download all periods** `payroll-registers_<first>_to_<last>.csv` (period_start, period_end, batch + the register columns; optional from/to). Every text cell formula-safe (D-68); payroll staff and admins only. OPEN and READY periods have no download. *Updates D-68, D-69 and D-123.* | B.4 FR-11, D-68 |
| D-136 | Payroll | **Carry-forward with registers** (updates D-121). A period is **closed** when its register is finalized or paid — or, for data from before registers, when it has an export batch. `carry_period` still starts from the later of the period after the corrected week and the most recent completed period, and takes the first one that isn't closed; so a correction to a week of a finalized or paid register is paid in the next register that isn't finalized. **Late approvals:** weeks approved after their own register was finalized (their people had a 0.00 line) stay CURRENT and are carried into the first not-closed period after their own, as carry-forward with their original weeks, and exported with that register — once. CURRENT adjustments left in a closed period are carried the same way. | B.4 FR-11 |
| D-137 | Payroll | **Earlier data, sync, seed.** `manage.py build_registers` (idempotent) gives every period that already has export batches a FINALIZED register — its batch, or several joined with `+` — built from exactly what was exported (no 0.00 lines), PAID when those batches were paid; leftover CURRENT weeks there become late approvals (D-136); PUBLISH audit row per register (system actor). `sync_payroll` runs the same step and reports `registers`; the out-of-sync banner also counts exported periods without a register. `seed_demo` finalizes & exports the older approved periods' registers through the real flow (their deadlines have passed) and pays all but the newest of them (updates D-73, D-126). | B.7, D-65, D-73 |
| D-138 | Payroll | **Pages.** `/payroll/` lists every ended pay period newest first: dates, status (Open, Ready, Finalized & exported, Paid), approved x of y, pay total, batch and the two downloads once finalized, plus "Download all periods"; older `?period=` links redirect to the period page. `/payroll/periods/<start>/`: status, approval deadline, the register (live preview or saved lines; carry-forward columns highlighted; totals row), the "Not approved yet" list, Finalize & export (confirmed in an in-page dialog) or the downloads and Mark as paid, then the week records and adjustments with their filters. **Corrections** links each adjustment to the register that pays it, with that register's status (updates D-124). | B.4 FR-11, D-124 |

---

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
- Every app uses a services package: <app>/services/<module>.py (e.g. payroll/services/publish.py,
  analytics/services/metrics.py); never a single services.py. Business rules live there as plain,
  tested functions. Views stay thin.
- Every view enforces permissions server-side via directory/services/permissions.py.
- Payroll models live only in the payroll database; no foreign keys across databases; payroll
  records are append-only as defined in B.12 D-15 (supersede, never edit). publish_period must be idempotent.
- Passwords: Argon2 first in PASSWORD_HASHERS; never log, print or store plain passwords.
- Durations are integer minutes; work dates are DateField; deadlines computed in COMPANY_TZ.
- Use TextChoices for all statuses. Every manager/admin/payroll action writes an AuditLog row
  (system actions use system_actor instead of actor, D-14).
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
✅ Verify: ends with "🎉 Ready to build."

### Phase 1 — Project scaffold + test setup
```
Plan first, then scaffold the project in the current folder:
- uv project pinned to Python 3.13; add django ">=5.2,<5.3", django-environ, argon2-cffi, django-axes,
  faker; dev deps: pytest, pytest-django, factory-boy, time-machine, pytest-cov,
  pytest-playwright, ruff.
- Django project package "config"; apps: directory, timesheets, audit, payroll, analytics, each with
  a services/ package (D-04).
- Two databases (default → db.sqlite3, payroll → payroll.sqlite3) and payroll/routers.py as in B.6.
- Custom User model (directory.User) with Team and Employee models exactly as in B.6 (including
  end_date), with AUTH_USER_MODEL set BEFORE the first migrate. Custom UserManager and the
  createsuperuser employee_code flow (D-02). directory/services/accounts.py sync_account called on
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
Eligibility rules in directory/services/signup.py. Configure django-axes (5 failures → 15-minute lock).
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
directory/services/permissions.py: reporting_tree (cycle-safe), is_manager, can_view, can_approve,
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
Calendar logic in timesheets/services/calendar.py, validation in timesheets/services/validation.py.
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
period resets that PeriodApproval to PENDING through timesheets/services/approvals.py in one
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
reopen_until per D-21 (D-07). Logic in timesheets/services/approvals.py, the only code that moves
weeks to/from APPROVED (D-10). Tests: T-29 to T-32, plus new catalogued tests for D-06, D-07, D-10, D-11.
```
✅ Verify: as eng.manager, approve the pending period for dev2 and reject one for dev1; dev1 sees the comment and can resubmit.

### Phase 8 — Payroll database (NEW)
```
Implement FR-11 and the payroll app (models only in the payroll database, as in B.6):
- payroll/services/ package (D-04): hours.py split_hours (overtime rule from B.1 row 16; Break time
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
Implement FR-5 on the home page with Chart.js. Metrics in analytics/services/metrics.py as tested pure
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

Use the demo logins from B.7 (password = `DEMO_PASSWORD`).

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
| 10 | payroll | Open Payroll for that period | New week records with regular/overtime/PTO split |
| 11 | payroll | Export CSV, then Mark paid | Records EXPORTED, then PAID |
| 12 | eng.manager | Edit a week in that paid period via change request | Payroll shows it under Corrections |
| 13 | eng.manager | Reject a period with a comment | Both weeks REOPENED; comment visible to the employee |
| 14 | eng.director | Open Team | Sees Priya and her reports |
| 15 | dev1 | Open /team/ and /payroll/ | Forbidden |
| 16 | dev1 | Add a work row 09:00–17:00 and a Break 12:00–12:30 the same day; then make them back-to-back | First refused as overlapping; then saved, and Hours worked excludes the Break (D-38, D-39, D-41) |

## D.2 Daily commands

```bash
cd ~/Documents/timesheet-app
uv run python manage.py runserver          # open http://127.0.0.1:8000
bash scripts/test_all.sh                   # all tests
uv run python manage.py backup_db          # back up both databases into backups/ (safe while running)
uv run python manage.py sync_payroll       # payroll out of sync? publish missing / supersede stale records
```
After new migrations:
```bash
uv run python manage.py migrate
uv run python manage.py migrate --database=payroll
```

To let others on a trusted office network use it: add your Mac's IP to `ALLOWED_HOSTS` in `.env`, run `uv run python manage.py runserver 0.0.0.0:8000`, and share `http://<your-mac-ip>:8000`. (Fine for a small team; for company-wide use, move to a server and PostgreSQL.)

> **Project location:** `~/Documents/timesheet-app`. If iCloud **Desktop & Documents Folders** syncing is on, turn it off (System Settings → [your name] → iCloud → iCloud Drive) — iCloud syncing can lock or corrupt the SQLite databases and upload thousands of Python files.

## D.3 Backups & reset

- **Backup:** `uv run python manage.py backup_db` saves timestamped copies of **both** `db.sqlite3` and `payroll.sqlite3` into `backups/`. Copy that folder somewhere safe.
- **Restore:** stop the server; pick **one timestamp** and copy `backups/db-<stamp>.sqlite3` over `db.sqlite3` and `backups/payroll-<stamp>.sqlite3` over `payroll.sqlite3` (always both from the same time); start the server, then run `uv run python manage.py sync_payroll` to repair any week approved after that backup. Keep the files you replaced until you have checked the result.
- **Start over with demo data (destroys all data):** stop the server, rename both `.sqlite3` files (e.g. add `-old`), then:
  ```bash
  uv run python manage.py migrate
  uv run python manage.py migrate --database=payroll
  uv run python manage.py seed_demo
  ```

## D.4 Troubleshooting

| Problem | Fix |
|---|---|
| Terminal shows `dquote>` or `quote>` | A pasted command was split. Press **Control + C** and copy it again from the .md file |
| `uv: command not found` | `brew install uv`, then open a new Terminal |
| Wrong Python version | `uv python install 3.13`, then `uv python pin 3.13` in the project folder |
| `ModuleNotFoundError` | Use `uv run python ...` (not plain `python`), or run `uv sync` |
| `no such table` | Run both migrate commands (D.2) |
| Payroll page empty after approving | `uv run python manage.py sync_payroll` |
| Port 8000 in use | `lsof -i :8000`, then `kill <PID>`; or `runserver 8001` |
| Deadline looks an hour off | Check `COMPANY_TZ` in `.env`; run the daylight-saving tests (T-15) |
| E2E tests fail with "browser not found" / "Executable doesn't exist" | `uv run playwright install chromium` (once), or `bash scripts/test_all.sh --browser-channel chrome` to use Google Chrome |
| A plain "Something went wrong" page | `DJANGO_DEBUG=False` hides details on purpose (D-96); read the Terminal running `runserver`, or set `DJANGO_DEBUG=True` in `.env` while investigating |
| Git shows the wrong author | Home-folder repository check (A.3) and `git config --show-origin user.name` |
| Claude Code uses API billing | Remove `ANTHROPIC_API_KEY` from `~/.zshrc`, open a new Terminal |
| `claude: command not found` | Open a new Terminal or `source ~/.zshrc` |
| "code: command not found" from Claude Code in Antigravity | Install the extension manually; the message is harmless |
| Hit the Claude usage limit | Wait for the reset (or enable extra usage), then continue the same phase |

## D.5 Future enhancements (after version 1)

- **Notifications** — in-app first, then email reminders via a local test mail server (Mailpit)
- Payroll export in your payroll provider's exact file format
- Company single sign-on instead of passwords
- Holiday calendar that pre-fills HOLIDAY entries
- Delegated approvals when a manager is on leave
- Move the payroll database (and then the app) to PostgreSQL on a server

---

## Quick start summary

1. **Part A:** run `doctor.sh` until it says "🎉 Ready to build."
2. **Part B:** review B.1 — especially the overtime rule (row 16).
3. **Part C:** create `~/Documents/timesheet-app`, add `docs/BUILD_GUIDE.md`, `scripts/doctor.sh` and `CLAUDE.md`, open it in Antigravity, then run Phases 0 → 12 — test with `scripts/test_all.sh` and commit after each.
4. **Part D:** walk through the acceptance checklist with the demo logins, and back up both databases regularly.
