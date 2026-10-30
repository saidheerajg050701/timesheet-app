# D-64: Overtime rule

- **Status:** Accepted
- **Area:** Payroll
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Payroll** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.1 row 16, B.9 #12.

## Decision

**Overtime rule**, per week: worked = Project work + Meetings + Training + Other; regular = min(worked, that week's prorated expected minutes, D-19); overtime = worked − regular; PTO, Sick and Holiday are separate totals, never overtime; Break never counts; total = regular + overtime + PTO + Sick + Holiday. Stored in minutes, shown as hours with 2 decimals.

## Consequences

- **Checked by:** [T-103](../testing.md#t-103)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/payroll/services/export.py`](../../apps/payroll/services/export.py), [`apps/payroll/services/hours.py`](../../apps/payroll/services/hours.py), [`apps/timesheets/templatetags/timesheet_tags.py`](../../apps/timesheets/templatetags/timesheet_tags.py)
- **Related decisions:** [D-19](D-019-add-employee-end-date-nullable-set-on.md)
