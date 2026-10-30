# D-107: Cells and slots

- **Status:** Accepted — later updated by D-127, D-128
- **Area:** Grid
- **From:** Change 2 – Weekly grid (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Grid** area, recorded during Change 2 – Weekly grid. It affects these parts of the specification: B.4 FR-8, D-35.

## Decision

**Cells and slots.** A cell is a button showing its hours (2 decimals) and opens a dialog for that row and day: work and Break cells hold one or more time slots (start, end, reason; "+ Add time slot", Remove; *"+ Add another time slot" since D-127*); leave cells hold hours and a reason (*optional since D-128*). Each slot is posted as one entry with the same `entry-N-*` fields as before (day, category and project fixed by its cell), so `parse_entries`, `validate_entries`, `save_week`, `edit_directly`, audit and approval/payroll hooks are reused unchanged; no model change, no migration. Slots left empty are dropped before posting; the server still ignores blank entries. "+ Add row" (HTMX, `timesheet_row`) offers a category and, for Project work, an active project (D-18); duplicates are refused (*superseded by D-127: "+ Add row" for an existing row points at it instead of showing an error*); a row added without slots survives a failed save (`grid-row` keys) and disappears after a successful one. *Since D-129 / D-130 a whole row can also be moved to another project or category, or deleted, from its "⋮" menu.*

## Consequences

- **Checked by:** [T-89](../testing.md#t-89), [T-90](../testing.md#t-90), [T-91](../testing.md#t-91), [T-161](../testing.md#t-161), [T-162](../testing.md#t-162), [T-166](../testing.md#t-166)
- **Cited in code:** [`apps/timesheets/forms.py`](../../apps/timesheets/forms.py), [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/static/timesheets/grid.js`](../../apps/timesheets/static/timesheets/grid.js), [`apps/timesheets/templates/timesheets/_grid.html`](../../apps/timesheets/templates/timesheets/_grid.html), [`apps/timesheets/templates/timesheets/_grid_slot.html`](../../apps/timesheets/templates/timesheets/_grid_slot.html), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/forms.py`](../../tests/forms.py), [`tests/timesheets/integration/test_grid.py`](../../tests/timesheets/integration/test_grid.py)
- **Related decisions:** [D-18](D-018-project-entries-must-have-an-active-project.md), [D-127](D-127-easier-multiple-time-slots.md), [D-128](D-128-optional-reason-on-time-entries.md), [D-129](D-129-row-actions.md), [D-130](D-130-row-action-rules.md)
- **Updated later by:** [D-127](D-127-easier-multiple-time-slots.md), [D-128](D-128-optional-reason-on-time-entries.md)
