# D-130: Change 7 – Row action rules

- **Status:** Accepted
- **Area:** Grid
- **From:** Change 7 – Edit or delete a whole row (commit `23439ce`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Grid** area, recorded during Change 7 – Edit or delete a whole row. It affects these parts of the specification: B.4 FR-8.

## Decision

**Change 7 – Row action rules** (one place: `grid_rows.py`). **Change project / category** moves every slot of the row to the chosen category (and active project for Project work, D-18; the same check as "+ Add row"); dates, times, hours and reasons are kept. Allowed: a work or Break row → any work category or Break (the dialog warns "Break is unpaid: these hours will no longer count as worked time", or that Break hours will count as worked time); a leave row → another leave type only, because leave has hours, not times. Anything else is refused (400) and nothing changes. If the chosen project / category **already has a row this week, the slots merge into it**; the dialog says so first ("… already has a row this week: the 3 time slots of this row will be added to it.") and the notice confirms it; overlaps and all other rules are checked as always when the week is saved (D-38). **Delete row** removes the row's slots for this week only. No schema change.

## Consequences

- **Checked by:** [T-193](../testing.md#t-193), [T-194](../testing.md#t-194), [T-195](../testing.md#t-195), [T-199](../testing.md#t-199), [T-231](../testing.md#t-231)
- **Cited in code:** [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/services/grid_rows.py`](../../apps/timesheets/services/grid_rows.py), [`apps/timesheets/static/timesheets/grid.js`](../../apps/timesheets/static/timesheets/grid.js), [`apps/timesheets/templates/timesheets/_row_actions.html`](../../apps/timesheets/templates/timesheets/_row_actions.html), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py), [`tests/timesheets/integration/test_row_actions.py`](../../tests/timesheets/integration/test_row_actions.py)
- **Related decisions:** [D-18](D-018-project-entries-must-have-an-active-project.md), [D-38](D-038-rows-with-times-on-the-same-day.md)
