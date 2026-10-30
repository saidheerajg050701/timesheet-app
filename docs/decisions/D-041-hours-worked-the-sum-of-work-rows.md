# D-41: Hours worked = the sum of work rows, excluding Break and leave

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-8, B.9 #16.

## Decision

Hours worked = the sum of work rows, excluding Break and leave. Shown per day and per week next to the expected hours, with separate Break and Leave totals and each day's first start and last end time.

## Consequences

- **Checked by:** [T-77](../testing.md#t-77), [T-184](../testing.md#t-184)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/services/summary.py`](../../apps/timesheets/services/summary.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py), [`tests/timesheets/integration/test_timesheet_flow.py`](../../tests/timesheets/integration/test_timesheet_flow.py)
