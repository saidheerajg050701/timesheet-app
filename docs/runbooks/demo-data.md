# Demo data

`seed_demo` builds a realistic fake company so every page has data from the first login. It
always builds the **same** company (fixed random seed 2026; dates relative to today), so tests and
screenshots are repeatable. The code is in `apps/directory/services/demo/`.

## Commands

```bash
uv run python manage.py seed_demo            # ~50 employees, 12 weeks of history
uv run python manage.py seed_demo --large    # ~500 employees, 52 weeks (performance testing)
uv run python manage.py import_employees data/your_file.csv   # create/update employees by employee_code
uv run python manage.py createsuperuser      # an admin login for an existing directory admin (asks for the employee code)
```
- `seed_demo` **refuses** when the database already has data — it never overwrites anything.
- It refuses an empty `DEMO_PASSWORD`, the example value from `.env.example`, and a password
  Django's rules reject ([D-146](../decisions/D-146-seed-demo-refuses-the-example-demo-password.md)).
- Every demo login uses the `DEMO_PASSWORD` from `.env` (stored only as an Argon2 hash).
- Rows the seed creates are audited with `system_actor="seed_demo"`; seeded human decisions name
  the manager as the actor ([D-14](../decisions/D-014-auditlog-actor-becomes-nullable-plus-a-new.md)).

## What gets created

| Item | What |
|---|---|
| Employees | ~50 across 6 departments and 9 teams, 4 management levels: the 13 core people in `data/employees_core.csv` plus generated staff (Faker) under the core managers |
| Login accounts | every active employee except the 3 sign-up test people |
| Projects | 8, coded by the app's own rule: **I-001 Customer Portal … I-007 Internal Operations**, and **I-008 Legacy Billing (closed)**, inactive ([D-155](../decisions/D-155-project-i-codes.md)); each with realistic **allowed tasks** |
| Tasks | the 9 standard tasks (PLN, DES, DEV, TST, REL, SUP, SEC, DOC, MTG); each project entry is booked to a task its project allows and the person's team usually does ([D-154](../decisions/D-154-demo-tasks-seed-demo.md)) |
| Timesheet history | the **6 finished pay periods** (12 weeks; 26 periods with `--large`) plus week 1 of the current period when today is in its week 2 ([D-27](../decisions/D-027-seed-history-is-aligned-to-pay-periods.md)). Mostly on time, some late, a few missed; work rows with realistic times (first start 08:00–09:30), a reason and a 30–60 minute lunch Break; leave as hours; public holidays named |
| Scenarios | one **rejected** period and one **open change request** (Platform team), one **manager edit** on request (Operations team) |
| Approvals | every older period is fully approved — locked weeks too, through the real approvals service, so they stay "not submitted by employee" ([D-144](../decisions/D-144-seed-change-9.md)). The **most recent finished period stays pending**, to try Approvals |
| Payroll database | filled after the main data is saved ([D-73](../decisions/D-073-seed-demo-fills-payroll-after-the-main.md)): the older periods' registers **finalized & paid** (by `payroll@`), the next one **finalized**, the newest approved period left to finalize; plus one **correction** (a week first paid one hour short, then corrected → a pay adjustment carried forward) |
| Pay | everyone has a pay record from the start of the history (or their hire date): salaried by job title (hourly rate = salary ÷ 2,080) or hourly for some titles; `dev1@` gets a 6 % raise part-way; **one Data-team person has no pay** ("Rate missing") ([D-172](../decisions/D-172-demo-pay-and-budgets.md)) |
| Budgets | I-001 … I-007 have budgets set from their approved cost so far, so the demo shows **On track**, **At risk** and **Over budget**; I-008 has none |

If the payroll part fails, the main data is kept and the summary says to run
`uv run python manage.py sync_payroll`.

## Logins

All use your `DEMO_PASSWORD`.

| Email | Who | Role(s) |
|---|---|---|
| `hr@yourcompany.com` | Lena Ortiz | Admin (Django Admin, everyone; approves the CEO) |
| `ceo@yourcompany.com` | Asha Rao | Admin + top-level manager (whole company) |
| `eng.director@yourcompany.com` | Mark Lee | Manager of managers |
| `eng.manager@yourcompany.com` | Priya Shah | Manager (approvals, change requests) |
| `dev1@yourcompany.com`, `dev2@yourcompany.com` | John Kim, Sara Ng | Employees |
| `ops.manager@yourcompany.com` | Tom Hall | Manager of a second team |
| `payroll@yourcompany.com` | Nina Patel | Payroll only |
| `finance.manager@yourcompany.com` | Omar Diaz | Payroll + manager |

### For trying sign-up

| Email | Expected result |
|---|---|
| `qa1@`, `ops1@`, `ops2@yourcompany.com` | ✅ allowed (in the directory, active, no account) |
| `former@yourcompany.com` | ❌ refused (INACTIVE) |
| `nobody@yourcompany.com` | ❌ refused (not in the directory) |
| `dev1@gmail.com` | ❌ refused (wrong domain) |
| `dev1@yourcompany.com` | ❌ "An account already exists" |

## Start over with fresh demo data

This replaces **all** data in the app. Stop the server, back up, then **move** the databases
aside (never delete them):
```bash
uv run python manage.py backup_db
mkdir -p backups/old && mv db.sqlite3 payroll.sqlite3 backups/old/
uv run python manage.py migrate
uv run python manage.py migrate --database=payroll
uv run python manage.py seed_demo
```
