# D-53: Payroll hook

- **Status:** Accepted
- **Area:** Payroll
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Payroll** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.9 #10/#13, C.4 P8.

## Decision

Payroll hook: `apps/timesheets/services/approvals.py → supersede_payroll_week(timesheet, actor, at)` is called for every week that leaves APPROVED; it does nothing until Phase 8 calls `apps/payroll/services/publish.py → supersede_week` (D-15).

## Consequences

- **Checked by:** [T-85](../testing.md#t-85)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py)
- **Related decisions:** [D-15](D-015-append-only-means-snapshot-and-hours-fields.md)
