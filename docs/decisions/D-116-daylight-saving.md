# D-116: Daylight saving

- **Status:** Accepted
- **Area:** Calendar
- **From:** Change 3 – Sunday-to-Saturday week (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Calendar** area, recorded during Change 3 – Sunday-to-Saturday week. It affects these parts of the specification: B.9 #2, T-15.

## Decision

**Daylight saving**: the US change on Sunday 2026-11-01 (and 2026-03-08) now falls on the first day of a week. Deadlines are built with `zoneinfo`, so Saturday 12:00 stays local either side; time entries remain wall-clock times as before (D-37).

## Consequences

- **Checked by:** [T-172](../testing.md#t-172)
- **Cited in code:** [`tests/timesheets/integration/test_sunday_week.py`](../../tests/timesheets/integration/test_sunday_week.py)
- **Related decisions:** [D-37](D-037-work-rows-project-work-meetings-training-other.md)
