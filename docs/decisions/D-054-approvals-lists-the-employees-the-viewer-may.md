# D-54: /approvals/ lists the employees the viewer may approve — direct reports, plus…

- **Status:** Accepted
- **Area:** Approvals
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Approvals** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-7, B.8.

## Decision

`/approvals/` lists the employees the viewer may approve — direct reports, plus no-manager employees for admins, never the viewer (D-11, D-31) — active employees employed on at least one day of the period, and inactive employees only if they have a timesheet in it (their existing timesheets can still be approved, D-19). Periods are 14 days from `PAY_PERIOD_ANCHOR`; default = the most recent completed period; the picker offers the current period and earlier; `?period=` takes any date and snaps to its period start.

## Consequences

- **Checked by:** [T-95](../testing.md#t-95), [T-97](../testing.md#t-97), [T-204](../testing.md#t-204)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`apps/timesheets/views/__init__.py`](../../apps/timesheets/views/__init__.py), [`apps/timesheets/views/approvals.py`](../../apps/timesheets/views/approvals.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py), [`tests/timesheets/integration/test_approvals.py`](../../tests/timesheets/integration/test_approvals.py)
- **Related decisions:** [D-11](D-011-nobody-can-ever-approve-their-own-timesheet.md), [D-19](D-019-add-employee-end-date-nullable-set-on.md), [D-31](D-031-admins-see-team-everyone-and-approvals-their.md)
