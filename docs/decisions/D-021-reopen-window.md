# D-21: Reopen window

- **Status:** Accepted
- **Area:** Timesheet status
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet status** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.4 FR-7/FR-8/FR-9, B.5, B.9, B.11 T-24/T-31/T-43, C.4 P6/P7, D.1.

## Decision

Reopen window: `reopen_until` = the later of (unlock/reject time + 48 hours) and the week's normal Saturday 12:00 deadline. When the window ends without resubmission, the week becomes LOCKED. Tested by T-43.

## Consequences

- **Checked by:** [T-24](../testing.md#t-24), [T-31](../testing.md#t-31), [T-43](../testing.md#t-43), [T-92](../testing.md#t-92), [T-219](../testing.md#t-219)
- **Cited in code:** [`apps/directory/services/demo/approvals.py`](../../apps/directory/services/demo/approvals.py), [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py), [`tests/timesheets/integration/test_approvals.py`](../../tests/timesheets/integration/test_approvals.py), [`tests/timesheets/integration/test_manager_decisions.py`](../../tests/timesheets/integration/test_manager_decisions.py), [`tests/timesheets/unit/test_calendar.py`](../../tests/timesheets/unit/test_calendar.py)
