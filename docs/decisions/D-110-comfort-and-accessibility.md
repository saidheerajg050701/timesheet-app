# D-110: Comfort and accessibility

- **Status:** Accepted
- **Area:** Grid
- **From:** Change 2 – Weekly grid (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Grid** area, recorded during Change 2 – Weekly grid. It affects these parts of the specification: B.10.

## Decision

**Comfort and accessibility**: live cell, row and footer totals while typing (convenience; the server recomputes, and the HTMX day summary still updates); the browser asks before leaving with unsaved changes (never after Save/Submit); cells are buttons with descriptive names ("I-001 Customer Portal / Project work, Mon Oct 26: 8.00 hours, 2 slots"; since D-127 followed by the slot times, and the cell shows "8.00 · 2 slots"); native `<dialog>`: focus moves in, Esc closes, focus returns to the cell; Enter inside a slot doesn't submit the week. On narrow windows the grid scrolls sideways with the first column fixed; the page itself never scrolls sideways. Vendored HTMX and plain JavaScript only (`apps/timesheets/static/timesheets/grid.js`).

*Paths updated in Refactor R3 to the app layout of Refactor R2 ([D-174](D-174-refactor-r2-own-apps-everything-in-apps.md)); nothing else changed.*

## Consequences

- **Checked by:** [T-167](../testing.md#t-167)
- **Cited in code:** [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/static/timesheets/grid.js`](../../apps/timesheets/static/timesheets/grid.js), [`apps/timesheets/templates/timesheets/_grid.html`](../../apps/timesheets/templates/timesheets/_grid.html), [`static/css/theme.css`](../../static/css/theme.css), [`tests/timesheets/integration/test_grid.py`](../../tests/timesheets/integration/test_grid.py)
- **Related decisions:** [D-127](D-127-easier-multiple-time-slots.md)
