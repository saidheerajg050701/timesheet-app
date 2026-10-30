# D-75: A week counts when its deadline has passed and the person was employed on at least one…

- **Status:** Accepted
- **Area:** Analytics
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Analytics** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-5/FR-8, B.9 #3, #15.

## Decision

A week counts when its deadline has passed and the person was employed on at least one weekday of it (D-19). **On time** = submitted, first submission on time (`is_late` False, D-52); **late** = submitted with `is_late`; **missed** = never submitted (no timesheet or no `submitted_at`). On-time rate = on time ÷ (on time + late + missed). `week_state().is_missed` uses the same rule, so `/timesheets/` and the dashboard agree: a re-locked week counts by its first submission; a missed week reopened but not yet resubmitted stays missed.

## Consequences

- **Checked by:** [T-116](../testing.md#t-116), [T-218](../testing.md#t-218)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/analytics/views/dashboard.py`](../../apps/analytics/views/dashboard.py), [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`tests/analytics/integration/test_analytics.py`](../../tests/analytics/integration/test_analytics.py), [`tests/timesheets/integration/test_manager_decisions.py`](../../tests/timesheets/integration/test_manager_decisions.py)
- **Related decisions:** [D-19](D-019-add-employee-end-date-nullable-set-on.md), [D-52](D-052-is-late-is-decided-by-the-first.md)
