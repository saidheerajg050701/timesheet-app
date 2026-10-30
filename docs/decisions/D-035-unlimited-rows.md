# D-35: Unlimited rows

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-8, C.4 P5.

## Decision

Unlimited rows: **Add row** (HTMX) adds as many rows as needed on any day of the week, and rows of an editable (draft) week can be removed. There is no row limit; the time rules and the 24-hour rule are the only limits. *Since Change 2 the rows are the time slots of the weekly grid (D-106, D-107); there is still no limit.*

## Consequences

- **Checked by:** [T-79](../testing.md#t-79), [T-89](../testing.md#t-89)
- **Cited in code:** [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/timesheets/forms.py`](../../apps/timesheets/forms.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py), [`tests/timesheets/integration/test_timesheet_flow.py`](../../tests/timesheets/integration/test_timesheet_flow.py)
- **Related decisions:** [D-106](D-106-weekly-grid.md), [D-107](D-107-cells-and-slots.md)
