# D-115: Week links use the Sunday

- **Status:** Accepted
- **Area:** Calendar
- **From:** Change 3 – Sunday-to-Saturday week (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Calendar** area, recorded during Change 3 – Sunday-to-Saturday week. It affects these parts of the specification: B.8.

## Decision

**Week links use the Sunday.** Any other date in `/timesheets/<date>/` (e.g. an old Monday link) or the Team week view redirects to the week that contains it; future weeks stay 404 (D-33). HTMX endpoints (day summary, add row) accept any date of the week.

## Consequences

- **Checked by:** [T-171](../testing.md#t-171)
- **Cited in code:** [`tests/timesheets/integration/test_sunday_week.py`](../../tests/timesheets/integration/test_sunday_week.py)
- **Related decisions:** [D-33](D-033-employees-can-open-only-the-current-week.md)
