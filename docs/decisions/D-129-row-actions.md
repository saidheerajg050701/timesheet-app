# D-129: Change 7 – Row actions

- **Status:** Accepted
- **Area:** Grid
- **From:** Change 7 – Edit or delete a whole row (commit `23439ce`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Grid** area, recorded during Change 7 – Edit or delete a whole row. It affects these parts of the specification: B.4 FR-8, B.10, D-49.

## Decision

**Change 7 – Row actions.** On an **editable** grid only — the employee's own open week (Draft, Reopened after an unlock or a rejection) and the manager's Edit directly — each row's label has a Bootstrap "⋮" dropdown (`aria-label="Row actions for I-001 Customer Portal"`) with **Change project / category** and **Delete row**; the menu opens below ⋮, aligned to its start, on top of everything in the table and never clipped (Popper `fixed` strategy, so the scrolling table and the rounded card can't clip it; the open menu's sticky name cell is raised above the other rows' sticky cells). Both open in the grid's native dialog, like "+ Add row" and the cells (never a browser `confirm()`); Esc or Cancel closes it and focus returns to ⋮. Delete asks first: "Delete I-001 Customer Portal? This removes 3 time slots (6.50 h) from this week." (leave: "leave entries"), counted from the grid as typed; a row without slots is removed at once. The action POSTs the whole week **as typed** (HTMX, CSRF) to `timesheet_rows` / `request_rows`; the server applies it with `apps/timesheets/services/grid_rows.py` and returns the re-drawn grid (row, day and week totals) with a status notice ("…Save to keep this change."); the day summary refreshes. **Nothing is saved until the week is saved** (Save draft / Submit through `save_week`, "Save and submit for the employee" through `edit_directly`), so every entry rule, status-on-read, the single Edit directly UPDATE audit row (before/after) and re-approval → publish → pay adjustments (D-118) are unchanged; leaving without saving warns as usual (D-110). **Server checks:** POST only; the employee's endpoint refuses a week that isn't editable (403, `WeekLocked`); Edit directly's needs an open change request the user may handle (403, D-47). Submitted, approved, exported and paid weeks stay read-only, with no menu; they change only through a change request.

## Consequences

- **Checked by:** [T-191](../testing.md#t-191), [T-192](../testing.md#t-192), [T-196](../testing.md#t-196), [T-197](../testing.md#t-197), [T-198](../testing.md#t-198), [T-199](../testing.md#t-199), [T-200](../testing.md#t-200), [T-202](../testing.md#t-202)
- **Cited in code:** [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/services/grid_rows.py`](../../apps/timesheets/services/grid_rows.py), [`apps/timesheets/static/timesheets/grid.js`](../../apps/timesheets/static/timesheets/grid.js), [`apps/timesheets/templates/timesheets/_grid.html`](../../apps/timesheets/templates/timesheets/_grid.html), [`apps/timesheets/templates/timesheets/_grid_row.html`](../../apps/timesheets/templates/timesheets/_grid_row.html), [`apps/timesheets/templates/timesheets/_row_actions.html`](../../apps/timesheets/templates/timesheets/_row_actions.html), [`apps/timesheets/views/approvals.py`](../../apps/timesheets/views/approvals.py), [`apps/timesheets/views/requests.py`](../../apps/timesheets/views/requests.py), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/e2e/helpers.py`](../../tests/e2e/helpers.py), [`tests/timesheets/integration/test_row_actions.py`](../../tests/timesheets/integration/test_row_actions.py)
- **Related decisions:** [D-47](D-047-requests-are-handled-by-whoever-can-approve.md), [D-110](D-110-comfort-and-accessibility.md), [D-118](D-118-settled-weeks.md)
