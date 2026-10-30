# D-60: Resubmitting a week of a REJECTED period sets the PeriodApproval back to PENDING…

- **Status:** Accepted
- **Area:** Approvals
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Approvals** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-7, B.5.

## Decision

Resubmitting a week of a REJECTED period sets the PeriodApproval back to PENDING (`approvals.period_resubmitted`, audited with the employee as actor).

## Consequences

- **Checked by:** [T-93](../testing.md#t-93), [T-219](../testing.md#t-219)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py), [`tests/timesheets/integration/test_manager_decisions.py`](../../tests/timesheets/integration/test_manager_decisions.py)
