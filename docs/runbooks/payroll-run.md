# Payroll run: one pay period, start to finish

What happens from the managers' approvals to "paid", who does what, and how corrections are
handled. The page-by-page help is in the [payroll user guide](../user-guides/payroll.md); the
design is in [architecture → Payroll](../architecture.md#payroll-append-only-by-design).

## The timeline

A pay period is two Sunday→Saturday weeks counted from `PAY_PERIOD_ANCHOR`.

| When | Who | What |
|---|---|---|
| Each Saturday 12:00 | employees | submit the week; unsubmitted weeks lock (missed) |
| After the period ends | managers | **Approvals**: approve or reject each person (locked people: edit, then approve, or reject) |
| By **Monday 12:00** after the period (`APPROVAL_DEADLINE_DAYS` = 2, `APPROVAL_DEADLINE_TIME` = 12:00) | managers | the approval deadline; after it, unapproved people show as **Overdue**. A reminder only |
| Once everyone is approved | payroll | the register is **Ready** → **Finalize & export** → download the CSVs |
| After the bank run | payroll | **Mark as paid** |

## Step by step

1. **Approvals come in.** Every approval writes one payroll record per week into
   `payroll.sqlite3` right after it is saved: regular hours up to the week's expected hours,
   overtime above, PTO / Sick / Holiday separately; Break never counts
   ([D-64](../decisions/D-064-overtime-rule.md), [D-65](../decisions/D-065-two-databases-fixed-order.md)).
2. **Watch the register** (`/payroll/` → the period). While it is **Open** you see how many people
   are approved and who is still pending. **Pending approvals** (`/payroll/pending/`, or the
   Admin header for HR) lists, per manager, who still has to be approved and why; download it as
   CSV to chase managers ([D-143](../decisions/D-143-pending-approvals-by-manager.md)).
3. **Ready.** The register turns **Ready** only when everyone who must be approved is approved —
   locked weeks included — and no change request is open. The deadline alone never makes it
   ready ([D-142](../decisions/D-142-the-register-waits-for-everyone.md)).
4. **Finalize & export.** Saves the register for good as one batch (e.g. `EXP-0007`): one line
   per employee with Week 1, Week 2, period hours, the carry-forward columns and the pay total
   ([D-135](../decisions/D-135-finalize-export-mark-as-paid-downloads.md)). Then download, as often as needed:
   - **Register CSV** — the register as shown;
   - **Detailed CSV** — one row per week and per adjustment;
   - **Download all periods** — every finalized register in one file.
5. **Mark as paid** once the money has gone out. The register and its records become PAID.

Every finalize, payment and sync writes an audit row.

## Corrections after a register is finalized

Payroll records are never edited ([D-15](../decisions/D-015-append-only-means-snapshot-and-hours-fields.md)).

1. An employee asks for a change; the manager unlocks or edits the week (a change request). The
   week's payroll record is **superseded** at once and its period goes back to pending.
2. After re-approval a **new version** is written. If the old version was in a finalized
   register, the new one is **SETTLED** and only the difference (e.g. +2.00 overtime or −1.50
   regular hours) becomes a **pay adjustment** ([D-118](../decisions/D-118-settled-weeks.md)–[D-122](../decisions/D-122-reason.md)).
3. The adjustment appears in the carry-forward columns of the **next register that isn't
   finalized yet** and is paid with it ([D-136](../decisions/D-136-carry-forward-with-registers.md)). Someone approved after their register was
   finalized is carried forward the same way.
4. **Corrections** (`/payroll/corrections/`) lists every changed week, the reason and the
   register that pays the difference.

## When payroll says "out of sync"

```bash
uv run python manage.py sync_payroll
```
Re-checks every approved period: publishes missing records, supersedes stale ones, creates
missing adjustments and registers. Safe to run any time and to repeat
([D-125](../decisions/D-125-audit-and-sync.md)). Run it also after [restoring a backup](backup-restore.md).

## Registers for older exports

Copies that exported payroll **before** registers existed (before Change 8) run this once:
```bash
uv run python manage.py build_registers
```
It builds a finalized (or paid) register for every period that was already exported, from
exactly what was exported; periods that already have a register are skipped
([D-137](../decisions/D-137-earlier-data-sync-seed.md)).
