# D-65: Two databases, fixed order

- **Status:** Accepted
- **Area:** Payroll
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Payroll** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-11, B.6, C.4 P8.

## Decision

**Two databases, fixed order.** The main DB decides first (PeriodApproval is the source of truth). The timesheet hooks only register `transaction.on_commit` callbacks; after the main commit, `publish_period` / `supersede_week` run in their own payroll transaction, then write PUBLISH / SUPERSEDE audit rows. A main rollback never reaches payroll; a payroll failure after the commit leaves the approval in place, rolls back the payroll write completely, is logged, shows an out-of-sync banner on `/payroll/`, and is repaired by `manage.py sync_payroll` (publish every APPROVED period, supersede live records of weeks no longer approved, one SYNC audit row).

## Consequences

- **Checked by:** [T-94](../testing.md#t-94), [T-107](../testing.md#t-107), [T-108](../testing.md#t-108), [T-109](../testing.md#t-109), [T-205](../testing.md#t-205)
- **Cited in code:** [`apps/directory/services/demo/__init__.py`](../../apps/directory/services/demo/__init__.py), [`apps/payroll/management/commands/sync_payroll.py`](../../apps/payroll/management/commands/sync_payroll.py), [`apps/payroll/services/publish.py`](../../apps/payroll/services/publish.py), [`apps/payroll/services/register/state.py`](../../apps/payroll/services/register/state.py), [`apps/payroll/services/sync.py`](../../apps/payroll/services/sync.py), [`apps/payroll/templates/payroll/_out_of_sync.html`](../../apps/payroll/templates/payroll/_out_of_sync.html), [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py)
