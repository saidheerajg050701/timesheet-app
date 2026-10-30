# D-106: Change 2 – Weekly grid

- **Status:** Accepted
- **Area:** Grid
- **From:** Change 2 – Weekly grid (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Grid** area, recorded during Change 2 – Weekly grid. It affects these parts of the specification: B.4 FR-8, B.8.

## Decision

**Change 2 – Weekly grid.** The week's entries are shown as a grid instead of a list: one row per Project / Category (project rows by code as "I-001 Customer Portal / Project work", then Meetings, Training, Other, "Break (unpaid)", then PTO, Sick, Holiday tagged "leave"); columns Mon–Sun headed with the day and date ("Mon" / "Oct 26, 2026"), then **Total worked hours**; a footer with Total worked hours per day and for the week. The footer counts work rows only; Break and leave rows show their own totals and are never added to it — exactly as `summarize` (D-39, D-41). The day summary (first start, last end, hours worked, expected, break, leave) stays below the grid. Week, deadline and pay periods are unchanged. *Column order superseded by D-111: the columns run Sun–Sat since Change 3.*

## Consequences

- **Checked by:** [T-160](../testing.md#t-160), [T-163](../testing.md#t-163), [T-166](../testing.md#t-166)
- **Cited in code:** [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/static/timesheets/grid.js`](../../apps/timesheets/static/timesheets/grid.js), [`apps/timesheets/templates/timesheets/_grid.html`](../../apps/timesheets/templates/timesheets/_grid.html), [`apps/timesheets/templates/timesheets/_grid_row.html`](../../apps/timesheets/templates/timesheets/_grid_row.html), [`static/css/theme.css`](../../static/css/theme.css), [`tests/e2e/helpers.py`](../../tests/e2e/helpers.py), [`tests/timesheets/integration/test_grid.py`](../../tests/timesheets/integration/test_grid.py)
- **Related decisions:** [D-39](D-039-new-category-break-break-time.md), [D-41](D-041-hours-worked-the-sum-of-work-rows.md), [D-111](D-111-weeks-run-sunday-saturday.md)
