# D-61: Payroll hook approvals.publish_payroll_period(approval, actor, at) is called inside…

- **Status:** Accepted
- **Area:** Payroll
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Payroll** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.9 #13, C.4 P8.

## Decision

Payroll hook `approvals.publish_payroll_period(approval, actor, at)` is called inside the approve transaction; since Phase 8 it only registers the payroll write to run after the main commit (see D-65).

## Consequences

- **Checked by:** [T-94](../testing.md#t-94)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py)
- **Related decisions:** [D-65](D-065-two-databases-fixed-order.md)
