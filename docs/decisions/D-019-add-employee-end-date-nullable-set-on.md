# D-19: Add Employee.end_date (nullable, set on deactivation)

- **Status:** Accepted
- **Area:** Data
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Data** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.1, B.4 FR-8/FR-11, B.6, B.9, C.4 P5/P8/P9/P11.

## Decision

Add `Employee.end_date` (nullable, set on deactivation). Entries are allowed only between `hire_date` and `end_date`. Expected hours for a partial week = `expected_weekly_minutes × active weekdays (Mon–Fri) / 5`. Weeks fully outside employment are never "missed". Existing timesheets of a deactivated employee can still be approved and paid.

## Consequences

- **Checked by:** [T-68](../testing.md#t-68), [T-69](../testing.md#t-69), [T-70](../testing.md#t-70), [T-105](../testing.md#t-105), [T-117](../testing.md#t-117), [T-137](../testing.md#t-137)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/directory/models.py`](../../apps/directory/models.py), [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/directory/services/demo/people.py`](../../apps/directory/services/demo/people.py), [`apps/directory/services/importer.py`](../../apps/directory/services/importer.py), [`apps/payroll/services/hours.py`](../../apps/payroll/services/hours.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`tests/analytics/integration/test_analytics.py`](../../tests/analytics/integration/test_analytics.py), [`tests/payroll/integration/test_payroll_publish.py`](../../tests/payroll/integration/test_payroll_publish.py), [`tests/payroll/unit/test_payroll_split.py`](../../tests/payroll/unit/test_payroll_split.py), [`tests/timesheets/unit/test_calendar.py`](../../tests/timesheets/unit/test_calendar.py), [`tests/timesheets/unit/test_validation.py`](../../tests/timesheets/unit/test_validation.py)
