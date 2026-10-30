# D-34: LOCKED and "missed" are worked out when read (effective_status, week_state)

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-8, B.5, B.9 #3, C.4 P5–P7.

## Decision

LOCKED and "missed" are worked out when read (`effective_status`, `week_state`); opening a page never writes. The stored status changes only through actions (save, submit, and later unlock/approve), so a locked week may still be stored as DRAFT.

## Consequences

- **Checked by:** [T-121](../testing.md#t-121), [T-131](../testing.md#t-131)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`tests/analytics/integration/test_analytics.py`](../../tests/analytics/integration/test_analytics.py), [`tests/analytics/integration/test_team.py`](../../tests/analytics/integration/test_team.py), [`tests/timesheets/integration/test_timesheet_flow.py`](../../tests/timesheets/integration/test_timesheet_flow.py)
