# D-127: Change 5 – Easier multiple time slots

- **Status:** Accepted — later updated by D-128
- **Area:** Grid
- **From:** Change 5 – Easier multiple time slots (commit `40e2f07`)
- **Recorded:** 2026-10-25

## Context

A decision in the **Grid** area, recorded during Change 5 – Easier multiple time slots. It affects these parts of the specification: B.4 FR-8, B.10.

## Decision

**Change 5 – Easier multiple time slots** (refines D-107 and D-110). Still **one row per Project / Category**; a second period of work on the same day is another time slot in the same cell. **"+ Add row" for a row that is already there** shows no error: the dialog closes, the existing row is scrolled into view and highlighted briefly (no animation with reduced motion), its first day cell gets focus, and a notice under the grid (`role="status"`) says "I-001 Customer Portal / Project work already has a row. Click a day to add another time slot (for example 2:00 PM – 5:00 PM)." (leave rows: "PTO already has a row. Click a day to enter or change its hours."). **Cell dialog:** the button reads "+ Add another time slot" (leave: "+ Add another leave entry"); a work or Break cell that already has slots opens with them listed plus one empty new slot, focused and ready to fill; a leave cell opens as before. An offered slot left empty is dropped when the dialog closes and never posted (as before). **Hint:** a cell with more than one slot shows "8.00 · 2 slots"; its tooltip (`title`) and accessible name list the slot times ("08:00–13:00, 14:00–17:00"; leave: hours) — rendered on the server (`Cell.slot_times`), kept up to date while typing, and shown on read-only grids too (submitted weeks, change requests, approvals, Team week view) as well as on Edit directly. **Rules unchanged:** 15-minute steps, no overlaps across all rows of a day, a reason on every slot (*optional since D-128*), Break never counted; the server's validation stays the authority.

## Consequences

- **Checked by:** [T-147](../testing.md#t-147), [T-167](../testing.md#t-167), [T-183](../testing.md#t-183), [T-184](../testing.md#t-184), [T-185](../testing.md#t-185), [T-186](../testing.md#t-186)
- **Cited in code:** [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/static/timesheets/grid.js`](../../apps/timesheets/static/timesheets/grid.js), [`static/css/theme.css`](../../static/css/theme.css), [`tests/e2e/test_timesheets.py`](../../tests/e2e/test_timesheets.py), [`tests/timesheets/integration/test_grid.py`](../../tests/timesheets/integration/test_grid.py)
- **Related decisions:** [D-107](D-107-cells-and-slots.md), [D-110](D-110-comfort-and-accessibility.md), [D-128](D-128-optional-reason-on-time-entries.md)
- **Updated later by:** [D-128](D-128-optional-reason-on-time-entries.md)
