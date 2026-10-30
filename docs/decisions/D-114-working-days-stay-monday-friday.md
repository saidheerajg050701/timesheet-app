# D-114: Working days stay Monday–Friday

- **Status:** Accepted
- **Area:** Calendar
- **From:** Change 3 – Sunday-to-Saturday week (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Calendar** area, recorded during Change 3 – Sunday-to-Saturday week. It affects these parts of the specification: B.9 #5, D-19.

## Decision

**Working days stay Monday–Friday** (D-19): `working_days(week_start)` = Mon…Fri (the week's days 2–6), used by expected hours and partial weeks, the day summary's expected column (and so the missing-day flag, D-55) and the seed. Sunday and Saturday are the weekend at the two ends of the week.

## Consequences

- **Checked by:** [T-168](../testing.md#t-168)
- **Cited in code:** [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`apps/timesheets/services/summary.py`](../../apps/timesheets/services/summary.py), [`tests/conftest.py`](../../tests/conftest.py), [`tests/timesheets/integration/test_change_requests.py`](../../tests/timesheets/integration/test_change_requests.py), [`tests/timesheets/integration/test_sunday_week.py`](../../tests/timesheets/integration/test_sunday_week.py), [`tests/timesheets/unit/test_calendar.py`](../../tests/timesheets/unit/test_calendar.py)
- **Related decisions:** [D-19](D-019-add-employee-end-date-nullable-set-on.md), [D-55](D-055-flags.md)
