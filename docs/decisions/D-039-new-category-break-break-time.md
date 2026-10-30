# D-39: New category BREAK ("Break time")

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.1 rows 15–16, B.4 FR-8, B.6.

## Decision

New category **BREAK** ("Break time"): needs start and end times, never a project, and is unpaid — never counted in Hours worked, overtime or payroll.

## Consequences

- **Checked by:** [T-75](../testing.md#t-75)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/timesheets/migrations/0002_entry_times_reason_break.py`](../../apps/timesheets/migrations/0002_entry_times_reason_break.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/summary.py`](../../apps/timesheets/services/summary.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py), [`tests/timesheets/unit/test_validation.py`](../../tests/timesheets/unit/test_validation.py)
