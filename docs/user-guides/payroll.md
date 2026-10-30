# Payroll guide

Payroll staff (the `is_payroll` flag) and admins see **Payroll** (`/payroll/`) and **Reports →
Project budget**. The payroll flag shows approved hours only — never other people's timesheet
details, notes or analytics. The whole run from approvals to paid, and how corrections work, is in
the [payroll run](../runbooks/payroll-run.md).

## Where the numbers come from

Each approved week is copied into a separate database, `payroll.sqlite3`, right after the
approval is saved:
- **regular** hours up to that week's expected hours, **overtime** above;
- **PTO**, **Sick** and **Holiday** separately (never overtime);
- **Break** is unpaid and never counted.

These records are never edited: a changed week gets a new version, and anything already paid is
corrected with a **pay adjustment**.

## Registers

`/payroll/` lists every ended pay period, newest first. Open one for its **register**: one line per
employee with Week 1, Week 2 and Period hours, the **carry-forward** columns (highlighted) and
the **Pay total**, plus a totals row.

| Status | Meaning | What you do |
|---|---|---|
| **Open** | approvals are still coming in; you see how many are approved and who is still pending (no hours yet) | chase managers with **Pending approvals** |
| **Ready** | everyone who must be approved is approved (locked weeks included) and no change request is open; the deadline alone never makes a period ready | **Finalize & export** |
| **Finalized & exported** | saved for good as one batch (e.g. `EXP-0007`) | download the files; pay; **Mark as paid** |
| **Paid** | done | — |

## Downloads

- **Register CSV** — the register as shown.
- **Detailed CSV** — one row per week and per adjustment (`row_type` WEEK / ADJUSTMENT).
- **Download all periods** — every finalized register in one file.

Download them as often as you like; they never change once the register is finalized. Cells that
start like a spreadsheet formula are made safe.

## Pending approvals

`/payroll/pending/` lists, per manager, who still has to be approved in a period and why — also as
CSV. HR sees the same list in the Admin header.

## Corrections

`/payroll/corrections/` lists every change to a week that had already been in a finalized
register: the reason, the difference (for example +2.00 overtime or −1.50 regular hours) and the
register that pays it. The difference goes into the carry-forward columns of the **next register
that isn't finalized yet**. Someone approved after their register was finalized is carried
forward the same way.

## "Payroll is out of sync"

If the page says so, ask whoever runs the app to run
`uv run python manage.py sync_payroll` (safe to repeat; see the
[payroll run](../runbooks/payroll-run.md#when-payroll-says-out-of-sync)).

## Reports → Project budget

Payroll sees **everyone's** labour cost (view only): each approved project hour × the person's
hourly rate on that day, against each project's budget — the same page managers have for their
people ([manager guide](manager.md#reports--project-budget)). Salaries and pay history are for HR
admins only.

Your own timesheet, Dashboard and Project hours work as for every employee
([employee guide](employee.md)).
