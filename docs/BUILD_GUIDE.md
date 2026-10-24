# Employee Timesheet Web App — Local Build Guide
## Python + Django · macOS · Google Antigravity · Claude Code

- **Audience:** You (the project owner), building the app with Claude Code inside the Google Antigravity IDE
- **Target:** A web application that runs entirely on your Mac (localhost), with local databases
- **Version:** 2.2 — October 21, 2026

### What changed

| Version | Change | Details |
|---|---|---|
| 2.2 | **Decisions log** | New **section B.12** (D-01…D-22) settles the open points from the spec review. B.1–B.11 and Part C updated to match; **B.12 wins** if anything still conflicts |
| 2.1 | **Payroll database** | Approved hours per week are copied into a **separate payroll database**. Only the new **Payroll** role (and admins) can see and export it (B.4 FR-11, B.6, Phase 8) |
| 2.1 | **Full testing plan** | New **section B.11**: test tools, folder layout, 40+ named test cases, example test code, coverage targets, and a one-command test runner. Tests use their own temporary databases |
| 2.1 | **Bigger demo data** | ~50 employees across 6 departments; most already have accounts and 12 weeks of timesheet history; approved weeks already in the payroll database; a few employees left without accounts to test sign-up (B.7) |
| 2.1 | **Password security** | Passwords are stored with **Argon2 hashing** — one-way protection that nobody, including admins, can reverse (B.4 FR-2, B.10) |
| 2.1 | Copy-safe commands | Part A checks are now short commands, so they copy correctly from the PDF |
| 2.0 | Tech stack | Switched to **Python + Django** |
| 2.0 | Notifications | Not included in version 1 |

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
| 9 | Work week | Monday → Sunday; a week is identified by its Monday | Default |
| 10 | Weekly deadline | **Saturday 12:00 noon** company time, same week. Weekend hours may be entered in advance (D-09) | **Decided** |
| 11 | Missed deadline | Week becomes **LOCKED** (missed). It must be unlocked — via the employee's **Change Request** or by the manager from the approval page — and then submitted. An unused reopen window returns the week to LOCKED (D-06, D-08) | **Decided** |
| 12 | Biweekly period | 2 weeks, anchored on Monday `2026-01-05` — `.env` → `PAY_PERIOD_ANCHOR` | Default |
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
PAY_PERIOD_ANCHOR=2026-01-05
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
| HR admin screens | **Django Admin** + **django-import-export** | Ready-made screens; CSV import/export |
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

**FR-6 Team analytics (hierarchy).** For managers; filters: direct reports vs whole tree, team, date range.
- Team hours per week, average utilization
- Per-employee table: hours, utilization %, on-time rate, late/missed weeks, pending approvals
- This week's compliance: who hasn't submitted yet
- Hours by project across the team
- Click anyone in the tree → read-only view of their analytics and timesheets

**FR-7 Biweekly approvals page.** For managers (and Admins, for employees with no manager). Nobody sees their own row (D-11). Details settled in B.12 D-54–D-63 (rows and periods, flags, partial weeks, reject, open requests, unlock, resubmission, payroll hook, bulk approve).
- Pick a pay period (default: most recent completed)
- One row per direct report: week 1 and week 2 status, total hours, flags (late, overtime, missing days)
- Open a row → both weeks' entries → **Approve** or **Reject** (comment required)
- Approve **only** when both weeks are SUBMITTED (D-06)
- A LOCKED week shows an **Unlock** button: it creates a manager-authored ChangeRequest (status UNLOCKED) plus an audit entry and reopens the week until `reopen_until` (D-21); the employee then submits (D-06)
- **Bulk approve** for rows with no flags
- Reject → both weeks become REOPENED with `reopen_until` set per D-21, and the manager's comment is shown to the employee (D-07)
- **Reopen window (D-21):** `reopen_until` = the later of (unlock/reject time + 48 hours) and the week's normal Saturday 12:00 deadline

**FR-8 Weekly timesheet and deadline.** Each week is a list of entry rows, as many as needed (D-35). Every row has a date, a category, a project (Project work only, D-18) and a required reason (D-36). Work rows (Project work, Meetings, Training, Other) and **Break** rows have a start and end time in 15-minute steps on the same day; the hours are calculated from the times (D-37). Timed rows on one day must not overlap (D-38). Leave rows (PTO, Sick, Holiday) have hours only (D-40). Break time is unpaid (D-39). **Hours worked** = work rows only; the page shows it per day and per week next to the expected hours, with separate Break and Leave totals and each day's first start and last end (D-41). Each day's work + Break + leave is at most 24 hours (D-42). A week needs at least one entry to be submitted, and a week with only Break rows cannot be submitted (D-32, D-43). Only the current week and earlier open (D-33). Submit by **Saturday 12:00 noon** company time. Weekend hours may be entered in advance; any change after submitting goes through a change request (D-09). After submitting: read-only. After the deadline, an unsubmitted week is **LOCKED / missed** (worked out when the page opens, so no background job is needed). When a reopen window (unlock or reject; it ends at the later of +48 hours and the week's Saturday 12:00 deadline, D-21) ends without resubmission, the week becomes LOCKED; a week submitted after its original deadline keeps `is_late = True` (D-08). Weeks with no timesheet at all count as missed only while the person was employed (from `hire_date` to `end_date`); weeks fully outside employment are never missed (D-19).

**FR-9 Manager changes on request.** Rules settled in B.12 D-46–D-53 (which weeks, who handles, notes, edit/unlock behaviour, late flag, payroll hook).
1. Employee opens a submitted or locked week → **Request change** → writes a reason.
2. The manager's **Change Requests** page lists open requests (count shown in the menu).
3. Manager chooses **Reject**, **Unlock for employee** (open until the later of +48 hours and the week's Saturday 12:00 deadline, D-21; if unused, the week becomes LOCKED — D-08), or **Edit directly**.
4. Every manager/admin change creates an **Audit Log** entry: who, when, before and after values, linked request.
5. Editing a week in an approved period sets that approval back to PENDING — done only through `timesheets/services/approvals.py`, in the same transaction (D-10) — and the payroll record for that week is marked **superseded** (see FR-11).

**FR-10 Admin (HR).** Through Django Admin at `/admin/`: manage employees (CSV import, deactivate, set Payroll/Admin flags), teams, projects; read-only audit log; view all timesheets; reset passwords.

**FR-11 Payroll database (NEW).**
1. When a manager **approves** a biweekly period, the app writes **one payroll record per approved week** into the **separate payroll database**.
2. Each record is a **snapshot** at the moment of approval: Employee ID, name, department, team, week start, period start, **regular hours, overtime hours, PTO, Sick, Holiday, total hours**, expected hours, approver name, approval time.
3. Payroll records are **append-only** (D-15): snapshot and hours fields never change after creation. Only `status`, `export_batch`, `exported_at`, `paid_at` and `superseded_at` may change, and only forward: CURRENT → EXPORTED → PAID, and any status → SUPERSEDED. This is enforced in code and tested. If an approved week is later changed (FR-9), the old record is marked **SUPERSEDED** and, after re-approval, a **new version** is written. Payroll always sees the current version plus a history of corrections. Timesheets of an employee who has since been deactivated can still be approved and paid (D-19).
4. **Payroll page** (`/payroll/`), for Payroll and Admin only:
   - Filter by pay period, department, team, employee, status
   - Totals per employee per period (regular, overtime, PTO, sick, holiday)
   - **Export CSV** for the selected period → records are stamped with an export batch number and marked **EXPORTED**
   - **Mark as paid** → records become **PAID**
   - **Corrections** tab: weeks that changed after they were already exported or paid, so payroll can adjust the next run
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

**Reopen window (D-21):** `reopen_until` = the later of (unlock/reject time + 48 hours) and the week's normal Saturday 12:00 deadline. A week unlocked on Wednesday therefore stays editable until Saturday 12:00.

**Who may change APPROVED (D-10):** `PeriodApproval` is the source of truth. Only `timesheets/services/approvals.py` may move a `Timesheet.status` to or from APPROVED, in the same database transaction as the matching `PeriodApproval` change.

**Payroll record status (D-15):** `CURRENT` → `EXPORTED` → `PAID`, forward only; any of these → `SUPERSEDED` when the week changes. Only `status`, `export_batch`, `exported_at`, `paid_at` and `superseded_at` may ever change.

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
    week_start = models.DateField()        # always a Monday
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
    reason = models.CharField(max_length=255)  # required (D-36); was "notes" before Phase 5b
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
    period_start = models.DateField()      # Monday of week 1
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
        CURRENT="CURRENT"; EXPORTED="EXPORTED"; PAID="PAID"; SUPERSEDED="SUPERSEDED"
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
| 1 | `week_start_for(d)` → Monday of that week | `timesheets/services/calendar.py` |
| 2 | `deadline_for(week_start, tz)` → Saturday 12:00 company time | same |
| 3 | `effective_status(timesheet, now)` → DRAFT becomes LOCKED after deadline; REOPENED becomes LOCKED after `reopen_until` (D-08, D-21) | same |
| 4 | `pay_period_for(d, anchor)` → `(period_start, week1, week2)` | same |
| 5 | `expected_minutes_for(employee, week_start)` → `expected_weekly_minutes × active weekdays (Mon–Fri, within hire_date…end_date) / 5`; 0 for weeks fully outside employment (D-19) | same |
| 6 | `reporting_tree(employee)` → all reports, cycle-safe | `directory/services/permissions.py` |
| 7 | `can_view`, `can_approve`, `can_edit`, `can_access_payroll` — `can_approve` = direct manager, or Admin for employees with no manager, never self (D-11); payroll flag grants nothing beyond `/payroll/` (D-12) | same |
| 8 | `sync_account(employee)` → copies is_admin → is_staff/is_superuser, status → is_active, email (lower-cased) → User (D-13, D-20) | `directory/services/accounts.py` |
| 9 | `validate_entries(...)` → required reason ≤ 255 (D-36); work and Break rows: start/end in 15-min steps, end after start, same day (D-37), no overlaps (D-38); leave: hours only (D-40); dates in week and within hire_date…end_date (D-19); PROJECT ⇔ active project, Break never a project (D-18, D-39); work + Break + leave ≤ 24 h/day (D-42) | `timesheets/services/validation.py` |
| 10 | `approve_period`, `reject_period`, `reset_approval`, `unlock_week` — the **only** code that moves a week to/from APPROVED, in one transaction with PeriodApproval (D-06, D-07, D-10); `unlock_week` and `reject_period` set `reopen_until` per D-21 | `timesheets/services/approvals.py` |
| 11 | `check_signup_eligibility(email)` | `directory/services/signup.py` |
| 12 | `split_hours(entries, expected)` → regular / overtime / PTO / sick / holiday; Break time is excluded from regular hours and overtime (D-45) | `payroll/services/hours.py` |
| 13 | `publish_period(approval, …)` (idempotent, D-66), `supersede_week(...)`; run after the main commit by the timesheet hooks (D-65); `sync_payroll(at)` repairs (`payroll/services/sync.py`) | `payroll/services/publish.py` |
| 14 | `export_period(...)` (whole period, batch `EXP-0001`…, D-68), `batch_csv(...)` (spreadsheet-safe), `mark_paid(...)` (per batch, D-69), `corrections()` (D-70) — forward-only status changes (D-15) | `payroll/services/export.py` |
| 15 | Dashboard and team metrics (on-time rate, overtime, hours by project, missed weeks): `dashboard_for`, `punctuality`, `overtime`, `hours_by_project`, `hours_by_category`, `approval_outcomes` — built on `week_state`, `summarize` and `split_hours` (D-74–D-79) | `analytics/services/metrics.py` |
| 16 | `summarize(entries, employee, week_start)` → per day and week: Hours worked (work rows only), Break, Leave, expected, first start, last end (D-41) | `timesheets/services/summary.py` |

## B.10 Quality rules

- **Passwords:** Argon2 hashing (`PASSWORD_HASHERS` with `Argon2PasswordHasher` first); minimum 12 characters; plain passwords never logged, emailed, shown, or stored; admins can only reset.
- **Security:** CSRF protection, secure sessions, lockout via django-axes; every query permission-checked on the server; `.env`, `db.sqlite3` and `payroll.sqlite3` never committed; `DEBUG=False` in production mode.
- **Payroll integrity:** payroll records are append-only as defined in D-15 (snapshot and hours fields frozen; lifecycle fields move forward only; corrections by superseding); every publish, supersede, export, payment and sync writes an AuditLog row (PUBLISH / SUPERSEDE / EXPORT / PAY / SYNC, D-22).
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
  integration/
    test_auth_views.py
    test_timesheet_flow.py
    test_entry_form.py     # shared entry-row form: blank rows, re-render, hours (T-89–T-91)
    test_change_requests.py
    test_approvals.py
    test_payroll_publish.py
    test_payroll_pages.py  # /payroll/, export CSV, corrections, 403s (T-37–T-39, T-110, T-111)
    test_analytics.py
    test_admin.py
    test_import_employees.py
    test_layout.py         # menus, header, placeholder pages, profile (FR-4, D-30)
    test_seed_demo.py
  e2e/
    test_e2e_flows.py      # marked @pytest.mark.e2e
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
| T-12 | Calendar | `week_start_for` on each weekday and Sunday | Correct Monday |
| T-13 | Calendar | Deadline at Saturday 11:59:59 | Still open |
| T-14 | Calendar | Deadline at Saturday 12:00:00 | Locked |
| T-15 | Calendar | Week containing daylight-saving change (March and November) | Deadline still 12:00 local |
| T-16 | Calendar | `pay_period_for` across year boundary | Correct 2-week period |
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
| T-37 | Payroll | Export CSV | File contents correct; records EXPORTED with batch number |
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
| T-59 | Databases | django-axes and every other non-payroll app after migrating both databases | Their tables exist only in the main database; payroll database holds only `django_migrations` (+ payroll tables from Phase 8) |
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
| T-74 | Validation | Row with an empty reason or a reason over 255 characters | Rejected (D-36) |
| T-75 | Validation | Break with a project, or Break without times | Rejected (D-39) |
| T-76 | Validation | PTO/Sick/Holiday with a start or end time; work row without times | Rejected (D-37, D-40) |
| T-77 | Timesheet | Day with work, a Break and leave | Hours worked counts only work rows; Break and Leave shown separately; first start/last end; per-day and week totals (D-41) |
| T-78 | Timesheet | Submit a week whose only rows are Breaks | Refused; nothing submitted (D-43) |
| T-79 | Timesheet | 20 rows on one day, plus rows on other days | All saved and shown; no row limit; the 24-hour rule still applies (D-35, D-42) |
| T-80 | Seed | `seed_demo` history | Every week passes `validate_entries`; every row has a reason; timed rows have times; lunch breaks and leave rows exist; Break never has a project (D-44) |
| T-81 | Change request | Request on DRAFT, NOT_STARTED, REOPENED or future week; second OPEN request on a week | Refused; first request on SUBMITTED/LOCKED/APPROVED (incl. a missed week with no timesheet) accepted (D-46) |
| T-82 | Change request | Who handles: employee with a manager, the CEO (no manager), an admin's own request | Direct manager only; HR admin for the CEO; nobody handles their own; others get 403 on detail and actions (D-47) |
| T-83 | Change request | Raise, reject, unlock, edit | Each writes one AuditLog row (CREATE / REJECT / UNLOCK / UPDATE) with the right actor, linked request and before/after (D-48–D-50) |
| T-84 | Change request | Edit directly with an overlap, a missing reason, a Break with a project, a Break-only week, >24 h, no rows | Refused with the Phase 5b messages; nothing changed (D-49) |
| T-85 | Change request | Edit or unlock a week in an APPROVED period | PeriodApproval → PENDING, both weeks leave APPROVED, `supersede_payroll_week` called for each, in one transaction (D-10, D-53) |
| T-86 | Timesheet | Unlocked week from two weeks ago | Employee can open and save it until `reopen_until`; saves write an UPDATE audit with before/after; after the window → LOCKED (D-51) |
| T-87 | Timesheet | Late flag after reopening | Missed week unlocked and submitted later → is_late True; on-time week reopened and resubmitted after Saturday → stays on time (D-08, D-52) |
| T-88 | Layout | Open-request count in the menu | Handlers see "Change requests" with the count of open requests they may handle; employees without reports don't see it |
| T-89 | Timesheet | Save the week page or Edit directly with untouched blank rows (day pre-filled only) | Blank rows ignored, never validated; a row with only hours or only a reason is refused ("choose a category") |
| T-90 | Timesheet | Save with an error, then again, on the week page and Edit directly | The form is shown with exactly the posted rows; no extra blank rows are added on re-render |
| T-91 | Timesheet | Hours column on the week page and Edit directly | Calculated for every work/Break row from start/end (e.g. 08:30–12:00 → 3.50) on page load and after an error; read-only for timed rows, typed for leave |
| T-92 | Approvals | Unlock a LOCKED week from the approval page (with and without an open employee request; missed week with no timesheet) | REOPENED per D-21; manager-authored UNLOCKED ChangeRequest or the open request resolved; UNLOCK audit (D-06, D-59) |
| T-93 | Approvals | Reject with a comment, employee resubmits | Comment shown on the employee's week page; after resubmission the period is PENDING again (audited) and approvable once both weeks are submitted (D-07, D-60) |
| T-94 | Approvals | Approve calls the payroll hook inside its transaction | Hook called once with the approval; if the hook itself fails, nothing changes (PeriodApproval, weeks, audit). A failure of the later payroll *write* does not undo the approval — see T-107 (D-10, D-61, D-65) |
| T-95 | Approvals | Who sees and approves which rows | Manager: direct reports only (not indirect, never self); HR admin: the CEO; CEO never sees own row; approving self or a non-direct report → 403 (D-11, D-54) |
| T-96 | Approvals | Bulk approve | Only clean rows have a checkbox; posted ineligible rows are skipped with a reason; each eligible employee approved in its own transaction; summary of approved and skipped (D-63) |
| T-97 | Approvals | Pay-period dates | 14-day periods from the anchor; default = most recent completed period; any date snaps to its period start; future periods refused; Previous/Next links (D-54) |
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
| T-110 | Payroll | CSV cells starting with `=`, `+`, `-`, `@` (or tab/CR) | Escaped with a leading `'`; other cells unchanged; batch numbers sequential (D-68) |
| T-111 | Payroll | Who can open payroll pages | Payroll users and admins: 200; employee, manager, director: 403 on every payroll URL; a payroll user still gets 403 on others' timesheet details (D-12) |
| T-112 | Payroll | Mark as paid | EXPORTED → PAID for that batch only; CURRENT and later records untouched; PAY audit; repeating does nothing (D-69) |
| T-113 | Payroll | `backup_db` | Timestamped copies of both databases (same timestamp) that open with their tables (D-72) |
| T-114 | Seed | Payroll part of `seed_demo` | Every approved week has a live record; older periods EXPORTED/PAID with batches EXP-0001…; exactly one SUPERSEDED correction with its v2; EXPORT/PAY by payroll@ (D-73) |
| T-115 | Analytics | Range filter 4 / 12 / 26 weeks and an invalid value | Weeks end with the current week; counts change with the range; invalid → 12 (D-74) |
| T-116 | Analytics | On-time / late / missed edge cases: draft past deadline, no timesheet, late, reopened-and-resubmitted on-time week, missed week reopened and resubmitted, re-locked submitted week, missed week reopened but not resubmitted, current week | Classified per D-75 (first submission decides; never submitted = missed); current week not counted; the `/timesheets/` Missed badge agrees |
| T-117 | Analytics | New hire mid-range and a deactivated employee (end_date) | Weeks outside employment never shown, counted or missed; partial weeks prorated (D-19) |
| T-118 | Analytics | Overtime vs payroll | Dashboard overtime per approved week equals PayrollWeek.overtime_minutes; drafts excluded (D-76) |
| T-119 | Analytics | Own data only | `/` always shows the logged-in user's numbers; query parameters can't select another employee |
| T-120 | Analytics | Empty state (new hire, no timesheets) | Friendly messages instead of charts; page renders 200 (D-80) |
| T-121 | Analytics | Viewing the dashboard | No INSERT/UPDATE/DELETE; the same number of queries for 4 and 26 weeks (D-34, D-80) |
| T-122 | Analytics | Hours by category with Break and leave, approval outcomes, current-week card | Break shown apart and never in totals; outcomes per period with "in progress"; card shows the effective status and the server's deadline; chart data via `json_script` (D-77, D-78) |

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
    """E2E: sign-up refused for an email that is not in the directory."""
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
5. `uv run pytest -m e2e` — browser tests. Until Phase 12, if no tests are marked `e2e` the script prints `e2e: skipped - no e2e tests yet` and treats pytest exit code 5 ("no tests collected") as success **for this step only**. Phase 12 installs Chromium and makes this step mandatory (D-01).

```bash
bash scripts/test_all.sh
```
Run it at the end of **every** phase, before committing.

## B.12 Decisions log

Decisions made after the spec review (D-01–D-20 on October 21, 2026; D-21–D-45 on October 22, 2026; D-46–D-63 on October 23, 2026; D-64–D-80 on October 24, 2026). **If B.12 conflicts with anything else in this guide, B.12 wins.**

| ID | Area | Decision | Affects |
|---|---|---|---|
| D-01 | Setup | `test_all.sh`: when no tests are marked `e2e`, skip the e2e step and print `e2e: skipped - no e2e tests yet`; treat pytest exit code 5 as success **only** for that step. Phase 12 installs Chromium and makes e2e mandatory. | B.11, C.4 P1/P12 |
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
| D-15 | Payroll | "Append-only" means snapshot and hours fields never change after creation. Only `status`, `export_batch`, `exported_at`, `paid_at` and `superseded_at` may change, and only forward: CURRENT → EXPORTED → PAID, and any status → SUPERSEDED. Enforced in code and tested. | B.4 FR-11, B.5, B.6, B.9, B.10 |
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
| D-26 | Setup | Until Phase 11, Django Admin is view-only for every model (passwords shown only as a masked Argon2 summary). Phase 11 adds editing, deactivate and password reset together with their audit rows. | B.4 FR-10, C.4 P2/P11 |
| D-27 | Data | Seed history is aligned to pay periods: the 6 completed periods before the current one (26 with `--large`), plus week 1 of the current period when today is in its week 2 — 12 or 13 weeks. The current week is left empty. | B.7, C.4 P2 |
| D-28 | Login | django-axes locks by **account (email)**: 5 failed attempts lock that email for 15 minutes from any computer; `uv run python manage.py axes_reset` clears it (it clears all lockouts; `axes_reset_username <email>` clears just one). The email is trimmed and lower-cased before counting, the 5th failure already shows the locked page, and `axes.W006` (which recommends adding the IP address) is silenced for this reason. | B.4 FR-1, C.4 P3, D.1 |
| D-29 | Login | There is one login page, `/login/`. `/admin/login/` redirects there (keeping `?next=`); a logged-in employee without `is_admin` who opens `/admin/` gets 403. | B.8, C.4 P3/P11 |
| D-30 | Layout | Menu items for pages built in later phases (Timesheets, Requests, Team, Approvals, Payroll) link to simple "coming in a later phase" placeholder pages that already enforce the correct permission on the server, so menus and 403s can be tested from Phase 4. Later phases replace the views but keep the URLs and URL names. | B.8, C.4 P4–P10 |
| D-31 | Roles | Admins see **Team** (everyone) and **Approvals** (their direct reports plus employees with no manager, never themselves), even if they manage nobody. Managers see Team and Approvals for their own reports. Replaces "only for managers" in the C.4 Phase 4 prompt (B.1 row 14, B.3, D-11). | B.1, B.3, C.4 P4/P7/P10 |
| D-32 | Timesheet | Submitting requires at least one entry ("Add at least one entry before submitting"); leave is entered as PTO, Sick or Holiday. | B.4 FR-8, C.4 P5 |
| D-33 | Timesheet | Employees can open only the current week and earlier weeks; future weeks cannot be opened or saved. The current week can be submitted any time before Saturday 12:00, including weekend hours entered in advance (D-09). Future weeks are never counted as missed. | B.4 FR-8, B.8, C.4 P5 |
| D-34 | Timesheet | LOCKED and "missed" are worked out when read (`effective_status`, `week_state`); opening a page never writes. The stored status changes only through actions (save, submit, and later unlock/approve), so a locked week may still be stored as DRAFT. | B.4 FR-8, B.5, B.9 #3, C.4 P5–P7 |
| D-35 | Timesheet | Unlimited rows: **Add row** (HTMX) adds as many rows as needed on any day of the week, and rows of an editable (draft) week can be removed. There is no row limit; the time rules and the 24-hour rule are the only limits. | B.4 FR-8, C.4 P5 |
| D-36 | Timesheet | Every row has a date, category, project (Project work only, D-18) and a **required reason** (max 255 characters). `TimeEntry.notes` is renamed to `reason`. | B.4 FR-8, B.6 |
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
| D-49 | Change request | **Edit directly** uses the Phase 5b validation for the week's employee (times, reason, no overlaps, Break rules, 24 h, employment dates, no Break-only/empty week). The week becomes SUBMITTED (first-time `submitted_at`/`is_late` only if never submitted). If it was in an APPROVED period, `approvals.reset_approval` sets the period to PENDING, its approved weeks to SUBMITTED and calls the payroll hook, in the same transaction (D-10). Audit UPDATE stores before/after status and entries with times and reasons. | B.4 FR-9, B.5, B.9 #10 |
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
| D-66 | Payroll | A payroll record belongs to one approval decision (`approved_at` = `PeriodApproval.decided_at`): publishing the same decision again is a no-op; a live record from an older decision is superseded and the next version written. Partial unique constraint `one_live_record_per_week` (at most one non-SUPERSEDED record per employee and week). | B.6, B.9 #13 |
| D-67 | Payroll | Append-only (D-15) enforced in code: `PayrollWeek.save()` refuses changes to frozen fields and any move other than CURRENT→EXPORTED→PAID or →SUPERSEDED, each lifecycle field set once by its own move; `delete()`, `QuerySet.update()`, `bulk_update()` and `QuerySet.delete()` raise AppendOnlyError; the admin is view-only. | B.6, B.10 |
| D-68 | Payroll | Export CSV covers **all CURRENT records of the selected period** (filters only change the view) as one batch numbered `EXP-0001`, `EXP-0002`, …; a batch can be downloaded again without changing anything; every cell starting with `=`, `+`, `-`, `@`, tab or CR gets a leading `'` so Excel/Numbers never run it as a formula. | B.4 FR-11 |
| D-69 | Payroll | Mark as paid works per batch: its EXPORTED records become PAID (`paid_at`); anything else in the batch (e.g. superseded) is untouched. | B.4 FR-11 |
| D-70 | Payroll | Corrections = SUPERSEDED records that had been exported or paid, shown with their replacement version (or "waiting for re-approval") and the difference in hours. | B.4 FR-11 |
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
django-axes; django-import-export; Faker; Django templates + Bootstrap 5 + HTMX + Chart.js
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
  django-import-export, faker; dev deps: pytest, pytest-django, factory-boy, time-machine, pytest-cov,
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
project, start/end time or leave hours, reason; unlimited rows, D-35–D-43), 15-minute steps, live
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
| 5 | dev1 | Add rows with start/end times and a reason, Save draft, then submit before Saturday 12:00 | SUBMITTED, read-only |
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
- **Restore:** stop the server, copy the backup files over `db.sqlite3` and `payroll.sqlite3` (always restore **both from the same time**), start the server, then run `uv run python manage.py sync_payroll`.
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
| E2E tests fail with "browser not found" | `uv run playwright install chromium` |
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
