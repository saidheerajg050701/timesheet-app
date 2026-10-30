# D-71: The snapshot's expected_weekly_minutes is that week's prorated expected minutes (D-19)

- **Status:** Accepted
- **Area:** Payroll
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Payroll** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.6, B.4 FR-11.

## Decision

The snapshot's `expected_weekly_minutes` is that week's prorated expected minutes (D-19). Deactivated employees' approved weeks are published, exported and paid like anyone else's.

## Consequences

- **Checked by:** [T-105](../testing.md#t-105)
- **Cited in code:** [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/publish.py`](../../apps/payroll/services/publish.py), [`tests/payroll/integration/test_payroll_publish.py`](../../tests/payroll/integration/test_payroll_publish.py)
- **Related decisions:** [D-19](D-019-add-employee-end-date-nullable-set-on.md)
