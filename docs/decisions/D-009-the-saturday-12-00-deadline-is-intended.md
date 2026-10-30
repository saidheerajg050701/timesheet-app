# D-09: The Saturday 12:00 deadline is intended

- **Status:** Accepted
- **Area:** Timesheet status
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Timesheet status** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.1, B.4 FR-8.

## Decision

The Saturday 12:00 deadline is intended. Weekend hours may be entered in advance; any change after submitting goes through a change request.

## Consequences

- **Checked by:** [T-169](../testing.md#t-169)
- **Cited in code:** [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`tests/timesheets/integration/test_sunday_week.py`](../../tests/timesheets/integration/test_sunday_week.py), [`tests/timesheets/integration/test_timesheet_flow.py`](../../tests/timesheets/integration/test_timesheet_flow.py)
