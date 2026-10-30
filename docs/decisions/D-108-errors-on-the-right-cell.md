# D-108: Errors on the right cell

- **Status:** Accepted
- **Area:** Grid
- **From:** Change 2 – Weekly grid (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Grid** area, recorded during Change 2 – Weekly grid. It affects these parts of the specification: B.9 #9.

## Decision

**Errors on the right cell.** Messages are unchanged. Reading problems (`ParsedEntries.problems`) go to the slot's cell; rule messages go to every cell whose entry they name, matched with `validation.mentions(entry)` (the same "Tue 20 Oct, I-001 09:00–12:00" texts the messages are built from); an overlap marks both cells; the 24-hour rule marks the day's footer total; anything else (e.g. an empty week) is listed at the top. Marked cells are outlined with `aria-invalid`, list their messages inside the dialog, and the summary at the top links to them.

## Consequences

- **Checked by:** [T-91](../testing.md#t-91), [T-164](../testing.md#t-164), [T-185](../testing.md#t-185)
- **Cited in code:** [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`apps/timesheets/static/timesheets/grid.js`](../../apps/timesheets/static/timesheets/grid.js), [`apps/timesheets/templates/timesheets/_grid.html`](../../apps/timesheets/templates/timesheets/_grid.html), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/timesheets/integration/test_grid.py`](../../tests/timesheets/integration/test_grid.py)
