# D-111: Change 3 – weeks run Sunday → Saturday

- **Status:** Accepted
- **Area:** Calendar
- **From:** Change 3 – Sunday-to-Saturday week (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Calendar** area, recorded during Change 3 – Sunday-to-Saturday week. It affects these parts of the specification: B.1 row 9, B.9 #1, FR-8.

## Decision

**Change 3 – weeks run Sunday → Saturday** and are identified by their Sunday; `Timesheet.week_start` is always a Sunday. The rule lives only in `apps/timesheets/services/calendar.py` (`WEEK_START_WEEKDAY = 6`, `week_start_for`, `week_days` Sun…Sat); every page and service (timesheet list and week, grid and day summary columns, countdown, change requests, approvals and the pay-period picker, payroll labels/filters/CSV, dashboard, team analytics, seed) uses it. **Supersedes** B.1 row 9 (Monday → Sunday) and the column order of D-106.

## Consequences

- **Checked by:** [T-12](../testing.md#t-12), [T-168](../testing.md#t-168)
- **Cited in code:** [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py), [`tests/e2e/conftest.py`](../../tests/e2e/conftest.py), [`tests/e2e/helpers.py`](../../tests/e2e/helpers.py), [`tests/factories.py`](../../tests/factories.py), [`tests/timesheets/integration/test_sunday_week.py`](../../tests/timesheets/integration/test_sunday_week.py), [`tests/timesheets/unit/test_calendar.py`](../../tests/timesheets/unit/test_calendar.py), [`tests/timesheets/unit/test_validation.py`](../../tests/timesheets/unit/test_validation.py)
- **Related decisions:** [D-106](D-106-weekly-grid.md)
