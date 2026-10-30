# Changelog

Every phase and change of the Employee Timesheet App, newest first, with its commit. Decisions
(D-xx) are in [docs/decisions/](docs/decisions/README.md) and tests (T-xx) in
[docs/testing.md](docs/testing.md). The original phase prompts are in the historical
[build guide](docs/BUILD_GUIDE.md).

| Version | Change | Commit | Date |
|---|---|---|---|
| 4.1 | [Refactor R3 – Documentation](#41--refactor-r3--documentation) | not committed yet | 2026-10-30 |
| 4.0 | [Refactor R2 – Own apps; everything in apps/](#40--refactor-r2--own-apps-everything-in-apps) | `6421d8e` | 2026-10-30 |
| 3.9 | [Refactor R1 – Code layout](#39--refactor-r1--code-layout) | `228eae6` | 2026-10-30 |
| 3.8 | [Change 12 – Employee pay, project budgets and labour cost](#38--change-12--employee-pay-project-budgets-and-labour-cost) | `062a78f` | 2026-10-28 |
| 3.7 | [Change 11b – Only the report filters that make a difference](#37--change-11b--only-the-report-filters-that-make-a-difference) | `4dd8155` | 2026-10-28 |
| 3.6 | [Change 11 – Reports → Project hours](#36--change-11--reports--project-hours) | `23fcc6b` | 2026-10-28 |
| 3.5 | [Change 10b – Project I-codes and project search](#35--change-10b--project-i-codes-and-project-search) | `8c00c54` | 2026-10-28 |
| 3.4 | [Change 10 – Project tasks and charge codes](#34--change-10--project-tasks-and-charge-codes) | `22466dc` | 2026-10-28 |
| 3.3 | [README and first-run checks](#33--readme-and-first-run-checks) | `e17cc7d` | 2026-10-28 |
| 3.2 | [Change 9 – Managers decide everyone](#32--change-9--managers-decide-everyone) | `0f34b45` | 2026-10-26 |
| 3.1 | [Change 8 – Pay period register](#31--change-8--pay-period-register) | `85f22e2` | 2026-10-26 |
| 3.0 / 2.9 | [Changes 6 and 7 – Optional reason; edit or delete a whole row](#30--29--changes-6-and-7--optional-reason-edit-or-delete-a-whole-row) | `23439ce` | 2026-10-26 |
| 2.8 | [Change 5 – Easier multiple time slots](#28--change-5--easier-multiple-time-slots) | `40e2f07` | 2026-10-25 |
| 2.7 | [Change 4 – Automatic pay adjustments](#27--change-4--automatic-pay-adjustments) | `fc2606b` | 2026-10-25 |
| 2.6 / 2.5 | [Changes 2 and 3 – Weekly grid; Sunday-to-Saturday week](#26--25--changes-2-and-3--weekly-grid-sunday-to-saturday-week) | `39485cd` | 2026-10-25 |
| 2.4 | [Change 1 – Modern UI](#24--change-1--modern-ui) | `7f19f32` | 2026-10-24 |
| 2.3 | [Version 1 – Phases 0–12](#23--version-1--phases-012) | `9a54543` … `bad0b31` | 2026-10-22 – 2026-10-24 |
| 2.2 | [Decisions log](#22--decisions-log) | `93226f6` | 2026-10-22 |
| 2.0 – 2.1 | [Starter kit](#20--21--starter-kit) | `f734ae0` | 2026-10-21 |

## 4.1 – Refactor R3 – Documentation

Docs only; no code, template, migration or settings change.
- `docs/BUILD_GUIDE.md` split into [architecture](docs/architecture.md),
  [requirements](docs/requirements.md), [decisions](docs/decisions/README.md) (one file per
  decision, D-01 … D-174), [testing](docs/testing.md) (one table, T-01 … T-270),
  [runbooks](docs/runbooks/) and [user guides](docs/user-guides/); the guide stays as the
  historical build log with links to the new pages.
- New CHANGELOG, [CONTRIBUTING](CONTRIBUTING.md) and [LICENSE](LICENSE); a short README;
  CLAUDE.md points future work at the new docs.

## 4.0 – Refactor R2 – Own apps; everything in apps/

No change in behaviour ([D-174](docs/decisions/D-174-refactor-r2-own-apps-everything-in-apps.md)).
- New apps **projects** (projects, tasks, allowed tasks, budgets), **compensation** (pay records,
  the Pay pages and Pay CSV, who may see pay and costs) and **reports** (Project hours and
  Project budget with their downloads).
- Every app lives in `apps/` and is imported as `apps.<app>`, keeping its label, so tables,
  migrations and audit names are unchanged. Each app has its own templates and static files.
- Four state-only migrations (`projects/0001`, `timesheets/0010`, `compensation/0001`,
  `directory/0004`) move models without touching a table or a row.
- Admin pages for projects and tasks moved to `/admin/projects/…`; JS files are served from
  `/static/<app>/…`.
- Same 350 tests; coverage 98.25 % → 98.27 %.

## 3.9 – Refactor R1 – Code layout

No change in behaviour ([D-173](docs/decisions/D-173-refactor-r1-the-code-layout.md)).
- Settings package `config/settings/` (base, local — the default — test, and an unused
  production skeleton).
- View packages (`apps/timesheets/views/`, `apps/analytics/views/`); the largest services became
  packages that re-export their public names; "who still has to approve" moved to
  `apps/timesheets/services/pending.py`.
- Tests grouped by app (`tests/<app>/unit`, `tests/<app>/integration`, `tests/site/`, one
  browser-test file per area); a `Makefile` with everyday commands.
- Same 350 tests; coverage 98.24 % → 98.25 %.

## 3.8 – Change 12 – Employee pay, project budgets and labour cost

D-166 – D-172, T-258 – T-270. Migrations `directory/0003_payrecord`, `timesheets/0009_project_budget`.
- HR records each person's **pay** in Admin (admins only): Salaried (annual salary + an hourly
  rate, suggested as salary ÷ 2,080) or Hourly, from an effective date. Pay is history: every
  change or correction is a new record; back-dating re-prices work; every change is audited.
- Admin-only **Pay CSV** export and import (preview, line-numbered errors, all-or-nothing).
- Projects get an optional **budget** and a "costs count from" date.
- New **Reports → Project budget** for managers (their tree), payroll and HR (everyone): budget,
  cost to date, remaining, % used, status; cost by team or manager, task, pay type, pay period
  and employee; the **Rate missing** list. Approved hours only; overtime at the same rate.
- Two downloads: the costs file (Excel / CSV) and the hours file.

## 3.7 – Change 11b – Only the report filters that make a difference

D-165, T-254 – T-257. No migration.
- On Project hours a manager sees **People** only when someone under them manages people, and
  **Group by** only when both team and manager would make a difference; the Excel skips the
  same tabs. An address with an option that isn't offered falls back to the default.

## 3.6 – Change 11 – Reports → Project hours

D-160 – D-164, T-244 – T-253. No migration; new package `openpyxl`.
- New **Reports** menu for everyone: **Project hours** with Period, Projects and Hours filters
  kept in the address. Employees see their own hours; managers their tree; directors all their
  managers' groups; admins everyone.
- Summary, by project (chart), by task, project × task, by week, non-project time; for managers
  by team or manager (own group and roll-up) and by employee.
- Excel and CSV downloads, formula-safe and audited; the same numbers from one service.

## 3.5 – Change 10b – Project I-codes and project search

D-155 – D-159, T-238 – T-243. Migration `timesheets/0008_project_i_codes`.
- Project codes **I-001, I-002, …** assigned by the app, never reused or edited; existing PRJ-xxx
  codes renamed to I-xxx. Charge codes become I-001-DEV.
- The project drop-down is a **search box** (I-code or name, keyboard friendly) with **Your
  recent projects** first, everywhere a week is edited.

## 3.4 – Change 10 – Project tasks and charge codes

D-148 – D-154, T-227 – T-237. Migrations `timesheets/0006_tasks`, `0007_default_tasks`.
- Project work is booked to a project **and a task** (9 standard tasks; admins add more and
  deactivate instead of deleting); each project has **Allowed tasks**.
- The **charge code** (project + task) is shown on every grid row; older work without a task
  shows "Task not recorded".
- Dashboard and Team add hours by task and by charge code. Payroll unchanged.

## 3.3 – README and first-run checks

D-145 – D-147, T-225, T-226.
- README starts with a 10-minute Quick start.
- `doctor.sh` answers "Ready to RUN" and "Ready to BUILD" separately and works on Linux.
- The example `DJANGO_SECRET_KEY` (or one under 50 characters) is refused for daily use, and
  `seed_demo` refuses the example `DEMO_PASSWORD`.

## 3.2 – Change 9 – Managers decide everyone

D-139 – D-144, T-217 – T-224. No migration.
- Managers can **edit, approve or reject** everyone whose weeks are submitted **or locked**;
  approving a locked week asks for a confirmation and marks it "Not submitted by employee" (still
  missed). Reopened weeks wait for the employee.
- A register is **Ready only when everyone is approved**; the deadline is a reminder (Overdue).
- New **Pending approvals by manager** page and CSV for payroll and HR.

## 3.1 – Change 8 – Pay period register

D-132 – D-138, T-203 – T-216. Migration `payroll/0003`.
- Each ended pay period has a **register** (one line per employee, carry-forward columns, pay
  total): Open → Ready → **Finalize & export** (one batch) → **Mark as paid**.
- Register CSV, Detailed CSV and "Download all periods"; the old any-time Export button is gone.
- `build_registers` for earlier exports; Approvals shows the approval deadline and Overdue.

## 3.0 / 2.9 – Changes 6 and 7 – Optional reason; edit or delete a whole row

Change 6: D-128, T-187 – T-190; migration `timesheets/0005`. Change 7: D-129 – D-131,
T-191 – T-202.
- The reason on a time slot is optional; read-only views show it only when entered.
- Each editable grid row has a **⋮** menu to change its project / category or delete it; nothing
  is saved until the week is saved.
- `/static/` files are revalidated on every page load.

## 2.8 – Change 5 – Easier multiple time slots

D-127, T-183 – T-186. No migration.
- "+ Add row" for an existing row points at it; a cell with slots opens with them listed plus an
  empty new one; cells show "8.00 · 2 slots".

## 2.7 – Change 4 – Automatic pay adjustments

D-118 – D-126, T-173 – T-181. Migration `payroll/0002_settled_weeks_and_adjustments`.
- A corrected week that was already exported or paid is **SETTLED**; the difference becomes a
  **pay adjustment** carried forward to the next pay run; Corrections shows each one;
  `sync_payroll` creates missing ones.

## 2.6 / 2.5 – Changes 2 and 3 – Weekly grid; Sunday-to-Saturday week

Change 2: D-106 – D-110, T-160 – T-167. Change 3: D-111 – D-117, T-168 – T-172.
- Timesheets are a **weekly grid** with time slots in an accessible dialog, used everywhere a week
  is shown.
- Weeks run **Sunday → Saturday**; the Saturday 12:00 deadline is the week's last day; pay periods
  are anchored on Sunday 2026-01-04 and a non-Sunday anchor stops the app.

## 2.4 – Change 1 – Modern UI

D-100 – D-105, T-157 – T-159.
- One theme stylesheet (`static/css/theme.css`), a shared status badge, chart colours from the
  theme, and a screenshot tool for visual review. Behaviour unchanged.

## 2.3 – Version 1 – Phases 0–12

D-23 – D-99, T-01 – T-156.

| Phase | What | Commit |
|---|---|---|
| 0 | Environment check (`doctor.sh`) | `f734ae0` (starter kit) |
| 1 | Project scaffold, two databases, Argon2, test setup | `9a54543` |
| 2 | Data model, `import_employees`, `seed_demo`, view-only admin | `ca271e8` |
| 3 | Login, sign-up with directory check, axes lockout | `09cc388` |
| 4 | Layout, profile and permissions | `8c00a4b` |
| 5 / 5b | Weekly timesheet, deadline, validation; start/end times, reasons, Break | `79d8314`, `abce157` |
| 6 | Change requests, unlock, Edit directly | `c7a2ea6` |
| 7 | Biweekly approvals, reject, unlock, bulk approve | `b46bb87` |
| 8 | Payroll database, publish/supersede, export, sync, backup | `e1833ba` |
| 9 | Personal analytics dashboard | `1ca56d5` |
| 10 | Team (hierarchy) analytics | `31aa771` |
| 11 | Admin polish: audited edits, deactivate, password reset, CSV | `f8513b8` |
| 12 | Full test pass, e2e, hardening, README | `bad0b31` |

## 2.2 – Decisions log

D-01 – D-22. A decisions log settling the open points of the spec review.

## 2.0 – 2.1 – Starter kit

The build guide (Python + Django; separate payroll database; Argon2 passwords; the testing plan;
bigger demo data; notifications out of scope), `CLAUDE.md`, settings, `doctor.sh` and the core
employees file.
