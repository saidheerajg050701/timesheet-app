# D-76: Dashboard overtime = payroll split_hours per week (prorated expected) summed over…

- **Status:** Accepted
- **Area:** Analytics
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Analytics** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-5.

## Decision

Dashboard overtime = payroll `split_hours` per week (prorated expected) summed over SUBMITTED and APPROVED weeks in the range, so approved weeks match the payroll records exactly.

## Consequences

- **Checked by:** [T-118](../testing.md#t-118)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/analytics/views/dashboard.py`](../../apps/analytics/views/dashboard.py)
