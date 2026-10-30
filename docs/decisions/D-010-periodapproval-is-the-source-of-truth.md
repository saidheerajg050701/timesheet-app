# D-10: PeriodApproval is the source of truth

- **Status:** Accepted
- **Area:** Timesheet status
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Timesheet status** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.4 FR-9, B.5, B.6, B.9.

## Decision

`PeriodApproval` is the source of truth. Only `apps/timesheets/services/approvals.py` may change `Timesheet.status` to or from APPROVED, in the same database transaction as the PeriodApproval change.

## Consequences

- **Checked by:** [T-85](../testing.md#t-85), [T-94](../testing.md#t-94)
- **Cited in code:** [`apps/directory/services/demo/approvals.py`](../../apps/directory/services/demo/approvals.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py), [`tests/timesheets/integration/test_change_requests.py`](../../tests/timesheets/integration/test_change_requests.py)
