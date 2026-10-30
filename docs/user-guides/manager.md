# Manager guide

You are a manager as soon as at least one person reports to you; directors see everyone below
them. On top of the [employee guide](employee.md) you get **Team**, **Approvals**, **Change
requests** and more in **Reports**. Nobody ever approves or handles their own timesheet.

## Approvals

**Approvals** (`/approvals/`): pick a **pay period** — 14 days, two Sunday-to-Saturday weeks. The
default is the most recent finished one.

- One row per **direct report** (HR admins: people with no manager): both weeks' status, hours
  worked (Break never counts), leave, and **Late / Overtime / Missing days** flags.
- Approve each period by **Monday 12:00** after it ends; after that, unapproved rows are marked
  **Overdue**. Payroll can pay the period only once **everyone** is approved.
- Open a person to see both weeks in the grid, then **Approve both weeks** or **Reject** (a
  comment is required; the employee sees it).

### When can I decide?
A period can be approved or rejected once its weeks are **submitted or locked**. If you can't, the
page lists why:
- a week is **reopened** — it waits for the employee until their window ends;
- a week of the running period hasn't been submitted yet;
- a **change request** is open — handle it first;
- the period is already approved.

### Locked people (never submitted)
- **Edit** the week in the grid (pre-filled with what they entered, or empty) and save. The week
  stays locked; it is marked **"Not submitted by employee"**.
- Then **Approve** — you are asked to confirm, because the hours go to payroll as approved while
  the week still counts as missed for the employee — or **Reject**.
- Or **Unlock week** for the employee: it reopens until the later of 48 hours from now and that
  week's Saturday 12:00 (recorded as a change request you made).

You can also **Edit** a submitted week before deciding; it stays submitted.

### Bulk approve
Tick clean rows — both weeks submitted, no flags, no open change request — and approve them
together.

## Change requests

**Change requests** (`/approvals/requests/`; the menu shows how many are open) lists requests
from the people you approve. Open one and choose:
- **Reject** — no change to the week; a note is optional.
- **Unlock** — the employee can edit until the later of 48 hours from now and the week's
  Saturday 12:00.
- **Edit directly** — change the week yourself with the same rules as the timesheet page; the
  week ends **submitted**.

Every step is in the audit log. Changing a week of an **approved** period puts that period back
to pending (approve it again) and supersedes its payroll record; if it was already paid, payroll
pays the difference in the next register.

## Team

**Team** (`/team/`) shows the people under you (admins: everyone). Filters: whole tree or direct
reports, team, last 4 / 12 / 26 weeks.
- Team hours per week against expected; average **utilization** (hours worked ÷ (expected −
  leave), finished weeks).
- A sortable table per person: hours, utilization, on-time rate, late / missed weeks, pending
  approvals.
- Who hasn't submitted this week; hours by project, by task and by charge code.
- Click a name for a **read-only** view of their dashboard and weeks.

## Reports → Project hours

`/reports/project-hours/` covers **you and everyone below you** (directors: all their managers'
groups). The [employee guide](employee.md#reports--project-hours) explains Period, Projects and
Hours. Managers also get:
- **Show people with no hours**;
- **People** (whole tree, direct reports only, or one manager's group) — shown only when someone
  under you manages people too;
- **Group by** team or manager — shown only when both would make a difference;
- **By manager** ("own group" adds up to the total; "including everyone below" is the roll-up;
  click a manager to look at their group) and **By employee**: everyone in scope, with 0.00 rows
  and a note such as "Hours not approved yet" or "On leave".

Excel and CSV downloads are written to the audit log. A shared link with an option you don't
have simply shows your default report.

## Reports → Project budget

`/reports/project-budget/` shows what **your people's approved hours** cost against each
project's budget.
- **Cost** = each approved project hour × the person's hourly rate on that day (set by HR),
  rounded to cents per entry. Only project work counts; overtime uses the same rate.
- Per project: **budget**, **total cost to date** (the whole project's approved cost since its
  "costs count from" date), **remaining**, **% used** and the status: **On track** (below 80 %),
  **At risk** (80–100 %), **Over budget** (above 100 %) or **No budget set**.
- **This period:** cost and hours by team or manager, task, pay type, pay period, and **By
  employee** (hourly rate used and cost). You never see anyone's salary or pay history.
- **Rate missing:** hours of someone with no pay record for those days are listed, not costed.
- Downloads: **Costs Excel / CSV** and **Hours Excel / CSV**; each is audited.
