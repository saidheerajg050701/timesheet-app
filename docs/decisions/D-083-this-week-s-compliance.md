# D-83: This week's compliance

- **Status:** Accepted
- **Area:** Team
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Team** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-6.

## Decision

**This week's compliance** lists everyone selected who is employed in the current week and hasn't submitted it (not SUBMITTED/APPROVED): "Not submitted yet" before Saturday 12:00, then "Missed" (never submitted, D-75), or "Reopened"/"Locked" for a week reopened after a submission.

## Consequences

- **Checked by:** [T-128](../testing.md#t-128)
- **Cited in code:** [`apps/analytics/services/team.py`](../../apps/analytics/services/team.py), [`apps/analytics/views/team.py`](../../apps/analytics/views/team.py), [`tests/analytics/integration/test_team.py`](../../tests/analytics/integration/test_team.py)
- **Related decisions:** [D-75](D-075-a-week-counts-when-its-deadline-has.md)
