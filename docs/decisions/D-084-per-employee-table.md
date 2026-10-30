# D-84: Per-employee table

- **Status:** Accepted
- **Area:** Team
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Team** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-6.

## Decision

Per-employee table: hours worked (all weeks, D-77), utilization (D-82), on-time rate, late and missed weeks (Phase 9 `punctuality`, D-75), overtime (Phase 9 `overtime` = payroll split, D-76), and **pending approvals** = finished pay periods in the range still PENDING (Phase 9 `approval_outcomes`, D-78). Sorted on the server with `?sort=<column>&dir=asc|desc`, ties by name; unknown columns sort by name.

## Consequences

- **Checked by:** [T-123](../testing.md#t-123)
- **Cited in code:** [`apps/analytics/services/team.py`](../../apps/analytics/services/team.py), [`apps/analytics/views/team.py`](../../apps/analytics/views/team.py), [`tests/analytics/unit/test_team_metrics.py`](../../tests/analytics/unit/test_team_metrics.py)
- **Related decisions:** [D-75](D-075-a-week-counts-when-its-deadline-has.md), [D-76](D-076-dashboard-overtime-payroll-split-hours-per-week.md), [D-77](D-077-the-hours-charts-use-every-saved-entry.md), [D-78](D-078-approval-outcomes.md), [D-82](D-082-utilization.md)
