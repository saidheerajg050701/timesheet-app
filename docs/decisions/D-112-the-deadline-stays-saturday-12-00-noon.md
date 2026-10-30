# D-112: The deadline stays Saturday 12:00 noon company time, now the last day of the week…

- **Status:** Accepted
- **Area:** Calendar
- **From:** Change 3 – Sunday-to-Saturday week (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Calendar** area, recorded during Change 3 – Sunday-to-Saturday week. It affects these parts of the specification: B.1 row 10, B.5, FR-8.

## Decision

The deadline stays **Saturday 12:00 noon company time**, now the **last day** of the week (`DEADLINE_DAY_OFFSET = 6`). D-09 still applies (the rest of Saturday may be entered in advance). LOCKED/missed, late (D-08, D-52), the reopen window (D-21: later of +48 h and that week's Saturday 12:00) and "missed = never submitted" (D-75) are unchanged.

## Consequences

- **Checked by:** [T-169](../testing.md#t-169)
- **Cited in code:** [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`tests/timesheets/integration/test_sunday_week.py`](../../tests/timesheets/integration/test_sunday_week.py)
- **Related decisions:** [D-08](D-008-when-a-reopen-window-unlock-or-reject.md), [D-09](D-009-the-saturday-12-00-deadline-is-intended.md), [D-21](D-021-reopen-window.md), [D-52](D-052-is-late-is-decided-by-the-first.md), [D-75](D-075-a-week-counts-when-its-deadline-has.md)
