# D-78: Approval outcomes

- **Status:** Accepted
- **Area:** Analytics
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Analytics** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-5.

## Decision

Approval outcomes: every pay period overlapping the range in which the person was employed, with its PeriodApproval status (no record = pending); the current, unfinished period is shown as "in progress" and not counted.

## Consequences

- **Checked by:** [T-122](../testing.md#t-122)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/analytics/views/dashboard.py`](../../apps/analytics/views/dashboard.py)
