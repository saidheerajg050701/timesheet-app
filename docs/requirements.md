# Requirements

What the app must do, as it works today (after Change 12 and Refactor R2). The detailed rules
are the decisions in [decisions/](decisions/README.md) — **a decision file wins over this page**.
How it is built: [architecture.md](architecture.md). How it is tested: [testing.md](testing.md).
How it grew: [CHANGELOG](../CHANGELOG.md) and the historical [BUILD_GUIDE](BUILD_GUIDE.md).

- [Defaults](#defaults)
- [Roles and permissions](#roles-and-permissions)
- [Features](#features) — FR-1 … FR-13
- [Timesheet status flow](#timesheet-status-flow)
- [Quality rules](#quality-rules)
- [Out of scope for version 1](#out-of-scope-for-version-1)

## Defaults

"Decided" rows are settled; "Default" rows can be changed (most are a line in `.env`).

| # | Topic | Value | Status |
|---|---|---|---|
| 1 | Tech stack | Python + Django ([architecture](architecture.md#tech-stack)) | Decided |
| 2 | Company email domain | `@yourcompany.com` — `.env` → `COMPANY_EMAIL_DOMAIN` | Decided |
| 3 | Demo data | ~50 fake employees, most with accounts and history ([demo data](runbooks/demo-data.md)) | Decided |
| 4 | Notifications | **Not in version 1** | Decided |
| 5 | Payroll data | Approved hours per week copied to a **separate payroll database**, seen only by Payroll and Admin | Decided |
| 6 | Password storage | **Argon2** one-way hashing | Decided |
| 7 | Testing | Automated tests for every change, plus browser tests ([testing](testing.md)) | Decided |
| 8 | Company time zone | `America/Chicago` — `.env` → `COMPANY_TZ` | Default |
| 9 | Work week | **Sunday → Saturday**; a week is identified by its Sunday ([D-111](decisions/D-111-weeks-run-sunday-saturday.md)) | Decided |
| 10 | Weekly deadline | **Saturday 12:00 noon** company time, the week's last day ([D-112](decisions/D-112-the-deadline-stays-saturday-12-00-noon.md)); the rest of Saturday may be entered in advance ([D-09](decisions/D-009-the-saturday-12-00-deadline-is-intended.md)) | Decided |
| 11 | Missed deadline | The week becomes **LOCKED** (missed). It can be unlocked (change request or the Approvals page) and submitted, or the manager can edit and approve it as it is ([D-139](decisions/D-139-managers-decide-every-required-person.md)) | Decided |
| 12 | Pay period | 2 weeks, counted from the **Sunday** `2026-01-04` — `.env` → `PAY_PERIOD_ANCHOR`; a non-Sunday stops the app ([D-113](decisions/D-113-pay-periods.md)) | Decided |
| 13 | Approver | **Direct manager**; higher managers view only. People with **no manager** are approved by an Admin. **Nobody approves their own timesheet** ([D-11](decisions/D-011-nobody-can-ever-approve-their-own-timesheet.md)) | Decided |
| 14 | Approval deadline | Managers approve each period by **Monday 12:00** after it ends — `.env` → `APPROVAL_DEADLINE_DAYS` (2), `APPROVAL_DEADLINE_TIME` (12:00); a reminder only ([D-133](decisions/D-133-approval-deadline-and-ready.md)) | Default |
| 15 | Time categories | **Work** (start/end times): Project work, Meetings, Training, Other. **Break** (start/end times, unpaid). **Leave** (hours only): PTO, Sick, Holiday ([D-37](decisions/D-037-work-rows-project-work-meetings-training-other.md), [D-39](decisions/D-039-new-category-break-break-time.md), [D-40](decisions/D-040-leave-rows-pto-sick-holiday-have-hours.md)) | Default |
| 16 | Overtime (payroll) | Per week: worked minutes up to that week's expected minutes are **regular**, the rest **overtime**; PTO, Sick, Holiday are separate and never overtime; Break never counts ([D-64](decisions/D-064-overtime-rule.md)) | Default — confirm with payroll |
| 17 | Hours granularity | 15-minute steps; at most 24 h a day; stored as whole minutes | Default |
| 18 | Expected hours | 40 h a week, can differ per employee; partial weeks (hire / end date) prorated by active weekdays ([D-19](decisions/D-019-add-employee-end-date-nullable-set-on.md)) | Default |
| 19 | Email verification at sign-up | Off (directory check only) | Default |
| 20 | Project codes | **I-001, I-002, …** assigned by the app, never edited or reused ([D-155](decisions/D-155-project-i-codes.md)) | Decided |
| 21 | Tasks | Project work is booked to a project **and** one of its allowed tasks; charge code = project + task, e.g. `I-001-DEV` ([D-148](decisions/D-148-tasks.md)–[D-151](decisions/D-151-the-entry-rule-for-tasks.md)) | Decided |
| 22 | Budget status | At risk from **80 %** used, Over budget above **100 %** — `.env` → `BUDGET_AT_RISK_PERCENT`, `BUDGET_OVER_PERCENT` ([D-169](decisions/D-169-cost-rules.md)) | Default |

All `.env` settings: [architecture → Settings and configuration](architecture.md#settings-and-configuration).

## Roles and permissions

| Capability | Employee | Manager | Payroll | Admin (HR) |
|---|---|---|---|---|
| Sign up / log in with company email; own profile | ✅ | ✅ | ✅ | ✅ |
| Enter and submit own weekly timesheet; raise a change request on own week | ✅ | ✅ | ✅ | ✅ |
| Own Dashboard | ✅ | ✅ | ✅ | ✅ |
| Team pages (analytics and read-only weeks) | — | ✅ own tree | — | ✅ everyone |
| Reports → Project hours (page, Excel, CSV) | ✅ own hours | ✅ own + tree (directors: all their managers' groups) | ✅ own hours | ✅ everyone |
| Approve / reject pay periods | — | ✅ direct reports | — | ✅ people with no manager (never self) |
| Edit a report's week (change request, or a submitted/locked week from Approvals) — audited | — | ✅ | — | ✅ |
| Payroll pages: registers, Finalize & export, Mark as paid, downloads, pending approvals, corrections | — | — | ✅ | ✅ |
| Manage employees, teams, projects, tasks, budgets; read the audit log (Django Admin) | — | — | — | ✅ |
| **Employee pay** — salaries, pay types, history, Pay CSV ([D-167](decisions/D-167-only-admins-see-or-change-pay.md)) | — | — | — | ✅ only |
| Reports → Project budget: labour cost, budget vs cost, per-person hourly rate and cost ([D-170](decisions/D-170-reports-project-budget-who-sees-what.md)) | — | ✅ own + tree (never salaries) | ✅ everyone (view only) | ✅ everyone |

- **Manager** is automatic: anyone with at least one person reporting to them.
- **Payroll** is the `is_payroll` flag on the employee; **Admin** is the `is_admin` flag.
- **Roles add up** ([D-12](decisions/D-012-roles-add-up.md)). Everyone is an employee first. The payroll flag only adds the Payroll
  pages and Project budget; it never shows other people's timesheet details. A payroll user who
  manages people has normal manager rights for their tree.
- `User.is_staff` / `is_superuser` always follow `Employee.is_admin`, and `User.is_active`
  follows `Employee.status`, on every save ([D-13](decisions/D-013-keep-user-is-staff-and-is-superuser.md)).
- Every page, filter and download checks permissions on the server
  ([architecture → Permissions](architecture.md#permissions)).

## Features

### FR-1 Login
Company email + password. Inactive employees cannot log in. **5 wrong passwords lock the account
for 15 minutes** (django-axes, per account, [D-28](decisions/D-028-django-axes-locks-by-account-email.md)). One login page for the app and the Admin ([D-29](decisions/D-029-there-is-one-login-page-login-admin.md)). No
self-service password reset: HR sets a temporary password and the person must choose a new one
at their next login ([D-91](decisions/D-091-password-reset-by-hr.md)).

### FR-2 Sign-up with directory check and secure password storage
1. The email is trimmed and lower-cased; it must end with `COMPANY_EMAIL_DOMAIN`.
2. It must belong to an **ACTIVE** employee in the directory who has no account yet.
3. Otherwise: *"This email is not in the company employee directory. Contact HR."* or
   *"An account already exists — please log in."*
4. Passwords: at least 12 characters plus Django's standard checks (not common, not all
   numbers, not too similar to the email).
5. **The password is never stored as typed**: only its Argon2 hash (one-way, salted) is saved.
   Nobody can read the original; forgotten passwords are reset, never shown.
6. The account email always mirrors the directory: `Employee.email` is the source of truth
   ([D-20](decisions/D-020-employee-email-is-the-source-of-truth.md)).

### FR-3 Local databases
Main data in `db.sqlite3`, payroll data in `payroll.sqlite3`. No cloud services
([architecture → Two databases](architecture.md#two-databases-and-the-router)).

### FR-4 Profile
The header and `/profile/` show full name, employee ID, job title, team, department, manager,
location and hire date — read-only, from the directory. Pay is never shown on a profile.

### FR-5 Dashboard (own analytics)
Rules: [D-74](decisions/D-074-dashboard-range-the-last-n-weeks-ending.md)–[D-80](decisions/D-080-charts-use-the-vendored-chart-js-with.md), [D-153](decisions/D-153-hours-by-task-and-by-charge-code.md). Range: last 4 / 12 / 26 weeks.
- This week's status with a live countdown to Saturday 12:00
- Hours worked per week vs expected (chart with target line)
- On-time / late / missed weeks; overtime (same rule as payroll)
- Hours by project, by category (Break shown separately, unpaid), **by task** and **by project +
  task (charge code)**; older project work without a task is its own "Task not recorded" line
- Approval outcome of each pay period
- Every chart also lists its numbers. A week never submitted counts as missed, even if it was
  approved later ([D-141](decisions/D-141-not-submitted-by-employee.md)).

### FR-6 Team (hierarchy analytics)
Rules: [D-81](decisions/D-081-who-is-on-team-whole-tree-the.md)–[D-86](decisions/D-086-performance.md), [D-153](decisions/D-153-hours-by-task-and-by-charge-code.md). For managers (their tree) and admins (everyone). Filters:
whole tree or direct reports, team, last 4 / 12 / 26 weeks.
- Team hours per week vs expected; average utilization (hours worked ÷ (expected − leave),
  finished weeks)
- A sortable table per person: hours, utilization %, on-time rate, late / missed weeks,
  pending approvals
- Who hasn't submitted this week
- Hours by project, by task and by charge code
- Click a name → a read-only view of that person's dashboard and weeks (`/team/<code>/`,
  `/team/<code>/weeks/<week>/`)

### FR-7 Pay-period approvals
Pay periods are 14 days, two Sunday→Saturday weeks counted from `PAY_PERIOD_ANCHOR`. For managers
(direct reports) and admins (people with no manager); nobody sees their own row. Rules:
[D-54](decisions/D-054-approvals-lists-the-employees-the-viewer-may.md)–[D-63](decisions/D-063-bulk-approve.md), updated by [D-139](decisions/D-139-managers-decide-every-required-person.md)–[D-141](decisions/D-141-not-submitted-by-employee.md).
- Pick a pay period (default: the most recent finished one). One row per person: both weeks'
  status, hours worked, leave and flags (Late, Overtime, Missing days). Rows not approved after
  the approval deadline are marked **Overdue**.
- Open a row → both weeks in the read-only grid → **Approve** or **Reject** (comment required).
- A period can be decided once every **required** week (one with at least one employed day) is
  **SUBMITTED or LOCKED**. A **REOPENED** week waits until its window ends; a running week that
  isn't submitted yet, an open change request, or an already approved period blocks the decision
  (`approvals.decision_blockers`, the one rule).
- **Locked weeks** (never submitted): the manager can **Edit** the week in the grid
  (`changes.edit_for_approval`), then approve it with the hours entered after a confirmation, or
  reject it. The week is marked "Not submitted by employee" and still counts as missed; an edit
  from Approvals never sets `submitted_at` ([D-140](decisions/D-140-edit-from-approvals.md), [D-141](decisions/D-141-not-submitted-by-employee.md)). A locked week also has
  **Unlock** (a manager-authored change request, audited).
- **Reject** reopens the required weeks with `reopen_until` per [D-21](decisions/D-021-reopen-window.md) and shows the comment
  to the employee; resubmitting makes the period pending again.
- **Bulk approve** only clean rows: both weeks submitted, no flags, no open change request.
- **Reopen window ([D-21](decisions/D-021-reopen-window.md))**: `reopen_until` = the later of (unlock or reject time + 48 hours)
  and the week's Saturday 12:00.

### FR-8 Weekly timesheet and deadline
Rules: [D-32](decisions/D-032-submitting-requires-at-least-one-entry-add.md)–[D-45](decisions/D-045-phase-8-split-hours-excludes-break-from.md), [D-106](decisions/D-106-weekly-grid.md)–[D-110](decisions/D-110-comfort-and-accessibility.md), [D-127](decisions/D-127-easier-multiple-time-slots.md)–[D-130](decisions/D-130-row-action-rules.md), [D-148](decisions/D-148-tasks.md)–[D-152](decisions/D-152-grid-rows-per-category-project-task.md), [D-157](decisions/D-157-project-search-box.md), [D-158](decisions/D-158-your-recent-projects.md).
- A week is a **grid**: one row per category, or per **project + task** for Project work (e.g.
  "I-001 Customer Portal · DEV Development", charge code I-001-DEV); columns Sun–Sat; a
  **Total worked hours** column and footer (work only; Break shown but never counted; leave
  shown separately).
- **+ Add row** picks a category; Project work also asks for a project (a search box: I-code or
  name; "Your recent projects" first — the week owner's projects of the 4 weeks before — then all
  active projects by I-code) and then one of that project's active allowed tasks. One row per
  category or project + task.
- Each row's **⋮** menu: **Change row** (another category, project or task; all slots move and
  merge into an existing row) or **Delete row** (after a confirmation). These only rewrite the
  grid as typed (`apps/timesheets/services/grid_rows.py`); nothing is saved until the week is
  saved ([D-129](decisions/D-129-row-actions.md), [D-130](decisions/D-130-row-action-rules.md)).
- Click a day cell: work and Break hold one or more **time slots** (start, end in 15-minute
  steps, same day, optional reason); leave holds hours and an optional reason. Timed rows must
  not overlap; work + Break + leave ≤ 24 h a day.
- Project work needs an active project and an active task allowed on it; older project work
  without a task shows "Task not recorded" and needs a task when the week is saved again
  ([D-151](decisions/D-151-the-entry-rule-for-tasks.md)).
- **Hours worked** = work rows only, per day and week, next to the expected hours, with Break
  and Leave totals and each day's first start and last end.
- To submit, a week needs at least one entry and not only Break rows. Only the current week and
  earlier can be opened.
- Problems are shown on their cell and in its dialog; the page warns before leaving with unsaved
  changes. The same grid is used read-only on submitted, approved and locked weeks, change
  requests, Approvals and Team.
- **Save draft** / **Submit** before **Saturday 12:00** company time. After submitting the week
  is read-only. An unsubmitted week becomes **LOCKED / missed** at the deadline (worked out when
  the page is read — no background job). A week submitted after its deadline keeps `is_late`.
  Weeks fully outside employment are never missed.

### FR-9 Changes on request
Rules: [D-46](decisions/D-046-a-change-request-can-be-raised-only.md)–[D-53](decisions/D-053-payroll-hook.md).
1. On a submitted, locked or approved week (up to the current week) the employee chooses
   **Request change** and writes a reason. `/requests/` lists their requests.
2. The request goes to whoever approves that person (admins for people with no manager; never
   oneself). **Change requests** (`/approvals/requests/`) lists the open ones; the menu shows the
   count.
3. The handler chooses **Reject**, **Unlock** (the employee can edit until the later of +48 h
   and the week's Saturday 12:00; if unused the week locks again) or **Edit directly** (same
   rules as the employee's page; the week ends SUBMITTED).
4. Every manager/admin change writes an **audit** row: who, when, before and after, the linked
   request.
5. Changing a week of an approved period sets the approval back to PENDING in the same
   transaction (only through `apps/timesheets/services/approvals.py`, [D-10](decisions/D-010-periodapproval-is-the-source-of-truth.md)) and supersedes the
   week's payroll record (FR-11).

### FR-10 Admin (HR)
Rules: [D-87](decisions/D-087-d-26-ends-for-directory-data-only.md)–[D-93](decisions/D-093-admin-access.md), [D-149](decisions/D-149-allowed-tasks-per-project.md), [D-155](decisions/D-155-project-i-codes.md), [D-166](decisions/D-166-employee-pay-is-history.md)–[D-168](decisions/D-168-project-budgets.md). Django Admin at `/admin/`, directory
admins only; every change is audited; nothing is deleted.
- **Employees:** add, edit, set the Payroll / Admin flags; **Deactivate / Reactivate** (asks for
  the end date, logs the person out; history stays and their weeks can still be approved and
  paid); **Reset password**; **Import CSV / Export CSV** (same columns; a summary or the errors
  before anything changes).
- **Teams**; **Projects** (the app assigns the next I-code; **Allowed tasks**; **Budget** and
  **Costs count from**); **Tasks** (code fixed once added; deactivate instead of delete).
- **Employee pay** on each employee's page: history and **Add pay change** (Salaried or Hourly,
  from an effective date; a new record every time; the same date corrects the earlier one);
  **Import / Export pay CSV** (checked first, only ever adds records).
- **Pending approvals** in the Admin header (read only).
- Timesheets, approvals, change requests, payroll records and the audit log are read-only.

### FR-11 Payroll database and registers
Rules: [D-64](decisions/D-064-overtime-rule.md)–[D-73](decisions/D-073-seed-demo-fills-payroll-after-the-main.md), [D-118](decisions/D-118-settled-weeks.md)–[D-126](decisions/D-126-seed.md), [D-132](decisions/D-132-pay-period-register.md)–[D-138](decisions/D-138-pages.md), [D-142](decisions/D-142-the-register-waits-for-everyone.md), [D-143](decisions/D-143-pending-approvals-by-manager.md).
1. When a period is **approved**, the app writes **one payroll record per approved week** into
   the **payroll database**, right after the approval is saved.
2. Each record is a **snapshot**: employee ID, name, department, team, week, period, regular,
   overtime, PTO, Sick, Holiday and total minutes, expected minutes, approver, approval time.
3. Records are **append-only** ([D-15](decisions/D-015-append-only-means-snapshot-and-hours-fields.md)): snapshot and hours never change; status only moves
   forward. A changed week's record is **SUPERSEDED** and a **new version** is written after
   re-approval. If an earlier version was already in a finalized register, the new version is
   **SETTLED** and the difference becomes a **pay adjustment**, carried to the next register
   that isn't finalized.
4. **Payroll** (`/payroll/`, payroll staff and admins): every ended pay period, newest first,
   with its **register** — one line per employee with Week 1, Week 2 and period hours, the
   carry-forward columns and the pay total, plus totals.
   - **Open**: approvals still coming in; **Pending approvals** (`/payroll/pending/`, also CSV)
     lists per manager who still has to be approved and why.
   - **Ready**: everyone who must be approved is approved (locked weeks included) and no change
     request is open; the deadline alone never makes a period ready.
   - **Finalize & export** saves the register once as one batch (`EXP-0007`); then the
     **Register CSV**, **Detailed CSV** and **Download all periods** can be downloaded any time.
   - **Mark as paid** closes it.
   - **Corrections** lists every changed week and the register that pays its difference.
5. The payroll flag never shows other people's timesheet details, notes or analytics.
6. The payroll database is a separate file: it can be backed up or handed over on its own.

### FR-12 Reports → Project hours
Rules: [D-160](decisions/D-160-reports-project-hours-who-sees-what.md)–[D-165](decisions/D-165-only-the-filters-that-make-a-difference.md). `/reports/project-hours/`, for everyone.
- **Who sees what:** employees (payroll too) only their own hours; managers themselves and
  everyone below them; admins everyone. Anything else is 403.
- **Filters** (kept in the address): Period (this / last pay period, last 4 or 12 weeks, or own
  dates — whole weeks, at most 53), Projects (search, several), Hours (Approved, Approved +
  Submitted, Everything entered). Managers also: Show people with no hours, and — only when they
  make a difference — People (whole tree, direct reports, one manager's group) and Group by
  (team or manager).
- **Shows:** project hours, non-project time (Meetings, Training, Other — never filtered by
  project) and total time; by project (chart), by task, project × task and by week; for managers
  by team or manager (own group and roll-up) and by employee (everyone in scope, zero rows with a
  note). Break and leave never count.
- **Downloads:** Excel (one tab per section) and CSV (one row per entry, never the reason); each
  download is audited.

### FR-13 Reports → Project budget and labour cost
Rules: [D-166](decisions/D-166-employee-pay-is-history.md)–[D-172](decisions/D-172-demo-pay-and-budgets.md). `/reports/project-budget/`, for managers (their tree), payroll and
admins (everyone).
- **Cost** = each approved project hour × the person's hourly rate on that day, rounded to cents
  per entry; only project work; overtime at the same rate; **approved hours only**.
- **Budget** per project: budget, total cost to date (since its "costs count from" date),
  remaining, % used and status (On track, At risk, Over budget, No budget set).
- **This period:** cost and hours by team or manager, task, pay type, pay period and by employee
  (rate used and cost); salaries are never shown.
- **Rate missing:** hours of someone without a pay record for that day are not costed (never $0)
  and are listed for HR.
- **Downloads:** Costs Excel / CSV and, separately, Hours Excel / CSV (the Project hours report
  with Approved); each is audited.

## Timesheet status flow

| From | Event | To |
|---|---|---|
| (none) | Employee saves the week | **DRAFT** |
| DRAFT | Employee submits before Saturday 12:00 | **SUBMITTED** |
| DRAFT or (none) | Saturday 12:00 passes without submitting | **LOCKED** (missed) |
| SUBMITTED or LOCKED (every required week) | Manager approves the period (a locked week after a confirmation) | **APPROVED** → payroll record written |
| SUBMITTED or LOCKED | Manager rejects the period | **REOPENED** (`reopen_until` per D-21) |
| LOCKED | Manager clicks **Unlock** on the Approvals page | **REOPENED**; a manager-authored change request + audit row |
| SUBMITTED or LOCKED | Manager edits the week from Approvals | unchanged (entries replaced, audited) |
| LOCKED / SUBMITTED / APPROVED | Change request → Unlock | **REOPENED**; an approved period goes back to pending, payroll superseded |
| LOCKED / SUBMITTED / APPROVED | Change request → Edit directly | **SUBMITTED**; an approved period goes back to pending, payroll superseded |
| REOPENED | Employee resubmits | **SUBMITTED** (`is_late` stays if past the original deadline) |
| REOPENED | `reopen_until` passes | **LOCKED** |

Only `apps/timesheets/services/approvals.py` moves a week to or from APPROVED, in the same
transaction as its `PeriodApproval` ([D-10](decisions/D-010-periodapproval-is-the-source-of-truth.md)). Diagram:
[architecture → Timesheet status flow](architecture.md#timesheet-status-flow).

## Quality rules

- **Security:** Argon2 passwords, login lockout, CSRF on every form, server-side permission
  checks on every page and download, `DEBUG` off for daily use, no secrets in Git
  ([D-96](decisions/D-096-debug-off-for-daily-use.md), [D-145](decisions/D-145-the-secret-key-can-t-stay-the.md)).
- **Correctness:** durations are whole minutes, money is `Decimal`; deadlines are computed in
  `COMPANY_TZ` including daylight saving ([D-116](decisions/D-116-daylight-saving.md)); every rule lives in one service function.
- **Audit:** every manager, admin and payroll action writes an audit row ([D-22](decisions/D-022-auditlog-actions-full-list.md)).
- **Speed:** the Team page and reports stay quick for ~500 employees and a year of data
  ([D-86](decisions/D-086-performance.md), [D-164](decisions/D-164-speed.md)).
- **Accessibility:** keyboard use, labels and focus on the grid and dialogs ([D-110](decisions/D-110-comfort-and-accessibility.md)).
- **Tests:** every rule has a catalogued test; `bash scripts/test_all.sh` passes before every
  commit ([testing](testing.md)).

## Out of scope for version 1

([D-99](decisions/D-099-known-limitations-of-version-1.md))
- Runs on one computer with SQLite over plain HTTP: fine for one person or a trusted office
  network, not for the internet (no HTTPS, [D-97](decisions/D-097-manage-py-check-deploy-https-only-warnings.md)).
- No notifications or email, so no "forgot password" link.
- No holiday calendar and no delegated approvals.
- One company time zone for all deadlines.
- The payroll CSV is the app's own format, not a payroll provider's.
- Changing someone's expected weekly hours applies to every week shown afterwards.
