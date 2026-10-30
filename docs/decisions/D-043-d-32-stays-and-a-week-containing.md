# D-43: D-32 stays, and a week containing only Break rows cannot be submitted either.

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-8.

## Decision

D-32 stays, and a week containing only Break rows cannot be submitted either.

## Consequences

- **Checked by:** [T-78](../testing.md#t-78)
- **Cited in code:** [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py), [`tests/timesheets/integration/test_timesheet_flow.py`](../../tests/timesheets/integration/test_timesheet_flow.py)
- **Related decisions:** [D-32](D-032-submitting-requires-at-least-one-entry-add.md)
