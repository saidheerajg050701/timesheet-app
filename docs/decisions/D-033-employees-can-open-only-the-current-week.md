# D-33: Employees can open only the current week and earlier weeks

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-8, B.8, C.4 P5.

## Decision

Employees can open only the current week and earlier weeks; future weeks cannot be opened or saved. The current week can be submitted any time before Saturday 12:00, including weekend hours entered in advance (D-09). Future weeks are never counted as missed.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py), [`tests/timesheets/integration/test_timesheet_flow.py`](../../tests/timesheets/integration/test_timesheet_flow.py), [`tests/timesheets/unit/test_calendar.py`](../../tests/timesheets/unit/test_calendar.py)
- **Related decisions:** [D-09](D-009-the-saturday-12-00-deadline-is-intended.md)
