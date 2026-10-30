# D-42: The 24-hour limit per day counts work, Break and leave rows together.

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-8, B.9, B.11 T-18.

## Decision

The 24-hour limit per day counts work, Break and leave rows together.

## Consequences

- **Checked by:** [T-18](../testing.md#t-18), [T-79](../testing.md#t-79)
- **Cited in code:** [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py)
