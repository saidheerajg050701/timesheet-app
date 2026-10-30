# D-113: Pay periods

- **Status:** Accepted
- **Area:** Calendar
- **From:** Change 3 – Sunday-to-Saturday week (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Calendar** area, recorded during Change 3 – Sunday-to-Saturday week. It affects these parts of the specification: B.1 row 12, FR-7.

## Decision

**Pay periods**: 14 days anchored on **Sunday 2026-01-04** (`PAY_PERIOD_ANCHOR`, settings default and `.env.example`). The anchor must be a Sunday: system check `timesheets.E001` makes `runserver`, `migrate`, `seed_demo` and every management command refuse to start with "PAY_PERIOD_ANCHOR … is a Monday; it must be a Sunday …", and `pay_period_for` raises `ValueError` for a non-Sunday anchor. Tests set the anchor themselves (`tests/conftest.py`), whatever `.env` says. **Supersedes** B.1 row 12 (Monday 2026-01-05).

## Consequences

- **Checked by:** [T-97](../testing.md#t-97), [T-170](../testing.md#t-170)
- **Cited in code:** [`apps/timesheets/apps.py`](../../apps/timesheets/apps.py), [`apps/timesheets/checks.py`](../../apps/timesheets/checks.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`config/settings/base.py`](../../config/settings/base.py), [`scripts/visual_review/test_screenshots.py`](../../scripts/visual_review/test_screenshots.py), [`tests/conftest.py`](../../tests/conftest.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py), [`tests/timesheets/integration/test_sunday_week.py`](../../tests/timesheets/integration/test_sunday_week.py), [`tests/timesheets/unit/test_calendar.py`](../../tests/timesheets/unit/test_calendar.py)
