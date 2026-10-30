# D-74: Dashboard range = the last N weeks ending with the current week (N = 4, 12 or 26

- **Status:** Accepted
- **Area:** Analytics
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Analytics** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-5.

## Decision

Dashboard range = the last N weeks ending with the current week (N = 4, 12 or 26; default 12; anything else → 12). The current week shows in the hours chart but counts for on-time / late / missed only after its Saturday 12:00 deadline.

## Consequences

- **Checked by:** [T-115](../testing.md#t-115)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/analytics/views/dashboard.py`](../../apps/analytics/views/dashboard.py), [`tests/analytics/integration/test_analytics.py`](../../tests/analytics/integration/test_analytics.py), [`tests/analytics/unit/test_metrics.py`](../../tests/analytics/unit/test_metrics.py)
