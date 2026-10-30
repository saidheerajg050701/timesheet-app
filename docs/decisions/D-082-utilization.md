# D-82: Utilization

- **Status:** Accepted
- **Area:** Team
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Team** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-6.

## Decision

**Utilization** = hours worked ÷ available hours, where available = prorated expected (D-19) − leave hours, summed over weeks in the range whose deadline has passed (the current week is not counted). Break never counts. "—" when nothing is available. Team average = total worked ÷ total available (weighted by available hours, not a mean of percentages).

## Consequences

- **Checked by:** [T-123](../testing.md#t-123), [T-124](../testing.md#t-124)
- **Cited in code:** [`apps/analytics/services/team.py`](../../apps/analytics/services/team.py), [`apps/analytics/views/team.py`](../../apps/analytics/views/team.py), [`tests/analytics/unit/test_team_metrics.py`](../../tests/analytics/unit/test_team_metrics.py)
- **Related decisions:** [D-19](D-019-add-employee-end-date-nullable-set-on.md)
