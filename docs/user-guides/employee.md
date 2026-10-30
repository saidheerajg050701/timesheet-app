# Employee guide

Everything every employee can do: log in, fill in the weekly timesheet, ask for a change, and
look at your own hours. Managers, payroll staff and HR are employees too, so this applies to
everyone. Other guides: [manager](manager.md), [payroll](payroll.md), [HR admin](hr-admin.md).

## Logging in

- Log in at `/login/` with your **company email** and password.
- **First time?** Choose **Sign up**: it works only for an ACTIVE employee in the company
  directory, with the company email domain, who has no account yet. Passwords need at least 12
  characters and must not be too common or too close to your email.
- **Five wrong passwords lock your account for 15 minutes.** There is no "forgot password" link:
  ask HR, who sets a temporary password; you choose a new one at your next login.
- Your menu: **Dashboard**, **Timesheets**, **Requests**, **Reports** and **Profile**. Managers
  also see Team and Approvals, payroll staff Payroll, HR Admin.
- **Profile** (`/profile/`) shows your directory details (read-only; HR changes them) and lets
  you change your password.

## Your weekly timesheet

`/timesheets/` lists your recent weeks. A week runs **Sunday to Saturday**.

### The grid
- One row per category, or per **project and task** for Project work; a column per day; a
  **Total worked hours** column and footer.
- **Project work** is always booked to a project **and** one of that project's tasks, e.g.
  "I-001 Customer Portal · DEV Development", with its **charge code** I-001-DEV. Meetings,
  Training, Other, Break and leave have no project and no task.
- Older project work saved before tasks existed shows **"Task not recorded"**: when you save that
  week again, choose a task for the row (⋮ → Change row).

### Adding rows
- **+ Add row** adds a category. Project work also asks for a **project** and then one of its
  active **tasks**. Each category, or project + task, has one row; adding one that is already
  there takes you to its row.
- **Finding a project:** type part of an I-code or a name ("i-002", "001", "portal" — any case),
  then click it or use ↑/↓ and Enter; Esc closes the list. With nothing typed you see **Your
  recent projects** (used in the 4 weeks before this week), then all active projects by I-code.
  "No matching project" means nothing fits; inactive projects never appear.

### Entering time
- **Click a day** to enter time. Work (Project work, Meetings, Training, Other) and **Break** use
  one or more **time slots**: a start and an end in 15-minute steps, on the same day, not
  overlapping, with an optional reason.
- **Leave** (PTO, Sick, Holiday) is hours only, with an optional reason.
- **Twice in a day** (e.g. 08:00–13:00 and 14:00–17:00 around a Break): click the day again —
  your slots are listed with an empty one ready — or use **+ Add another time slot**. The cell
  then shows e.g. "8.00 · 2 slots".
- A day's work + Break + leave is at most 24 hours.

### Fixing a row
Each row's **⋮** menu:
- **Change row** — another category, project or task; all its slots move (dates, times and
  reasons stay); if the new one already has a row they merge.
- **Delete row** — after a confirmation that shows how many slots and hours.

Both change the grid at once and are kept when you save the week.

### Totals
**Break is unpaid and never counted** in Total worked hours; leave is shown separately. Below the
grid, the day summary shows first start, last end, hours worked, expected hours, Break and Leave.

### Saving and the deadline
- **Save draft** any time; **Submit** before **Saturday 12:00 noon** company time. You may enter
  the rest of Saturday in advance.
- To submit, the week needs at least one entry, and not only Break.
- After submitting the week is read-only. A week not submitted by the deadline is **locked** and
  counts as **missed** — even if your manager approves it later.
- Only the current week and earlier weeks can be opened.
- Every rule is checked when you save; problems are shown on the cell they belong to. The page
  warns you before you leave with unsaved changes.

## Asking for a change

On a **submitted, locked or approved** week, **Request change** sends a reason to whoever approves
you (your manager; HR if you have none). `/requests/` lists your requests and their outcome:
- **Rejected** — nothing changes; the handler may add a note.
- **Unlocked** — you can edit and resubmit until the later of 48 hours from the unlock and the
  week's Saturday 12:00. If you don't resubmit in time the week locks again.
- **Edited** — your manager changed the week for you; it is submitted again.

If your manager **rejects** a pay period, both weeks reopen the same way and their comment is
shown on the week.

## Dashboard

The home page (`/`) shows your last 4, 12 or 26 weeks:
- this week's status with a live countdown to Saturday 12:00;
- hours worked per week against expected hours;
- on-time, late and missed weeks; overtime (the same rule as payroll);
- hours by project, by category (Break separately, unpaid), **by task** and **by project + task**
  (charge code, e.g. I-001-DEV; "Task not recorded" is its own line);
- the approval outcome of each pay period.

Every chart also lists its numbers.

## Reports → Project hours

`/reports/project-hours/` shows **your own** hours.
- **Period:** this or last pay period, last 4 or 12 weeks, or your own dates (whole
  Sunday–Saturday weeks, at most 53). **Projects:** type and pick one or more (none = all).
  **Hours:** Approved, Approved + Submitted, or Everything entered.
- It shows project hours, non-project time (Meetings, Training, Other — never filtered by
  project) and total time; by project (with a chart), by task, project × task and by week.
  Break and leave are never counted.
- **Excel** (one tab per section) and **CSV** (one row per entry, without reasons). The filters
  stay in the address, so you can bookmark a report.
