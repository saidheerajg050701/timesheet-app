# D-77: The hours charts use every saved entry in the range (drafts and the current week included)

- **Status:** Accepted
- **Area:** Analytics
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Analytics** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-5.

## Decision

The hours charts use every saved entry in the range (drafts and the current week included): Hours worked = work rows; by project = Project work rows; by category = work categories plus leave; Break is listed separately as unpaid and excluded from every total.

## Consequences

- **Checked by:** [T-122](../testing.md#t-122)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/analytics/services/team.py`](../../apps/analytics/services/team.py), [`apps/analytics/views/dashboard.py`](../../apps/analytics/views/dashboard.py)
