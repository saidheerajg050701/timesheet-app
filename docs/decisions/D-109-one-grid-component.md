# D-109: One grid component

- **Status:** Accepted
- **Area:** Grid
- **From:** Change 2 – Weekly grid (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Grid** area, recorded during Change 2 – Weekly grid. It affects these parts of the specification: B.8, D-85.

## Decision

**One grid component**: `apps/timesheets/templates/timesheets/_grid.html` (+ `_grid_row.html`, `_grid_slot.html`) built by `apps/timesheets/grid.py → build_grid`. Editable on the employee's week page and on Edit directly (same rules and audit as before); read-only on submitted, approved and locked weeks, the change-request detail, both weeks of the approval page and the Team week view, where a cell's dialog lists its slots' times, hours and reasons without inputs. It replaces `_row.html` and `timesheet.js`.

*Paths updated in Refactor R3 to the app layout of Refactor R2 ([D-174](D-174-refactor-r2-own-apps-everything-in-apps.md)); nothing else changed.*

## Consequences

- **Checked by:** [T-165](../testing.md#t-165)
- **Cited in code:** [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/static/timesheets/grid.js`](../../apps/timesheets/static/timesheets/grid.js), [`apps/timesheets/templates/timesheets/_grid.html`](../../apps/timesheets/templates/timesheets/_grid.html), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/timesheets/integration/test_grid.py`](../../tests/timesheets/integration/test_grid.py)
