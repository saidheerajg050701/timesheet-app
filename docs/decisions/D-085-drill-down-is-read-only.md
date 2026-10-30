# D-85: Drill-down is read-only

- **Status:** Accepted
- **Area:** Team
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Team** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.8, D-30.

## Decision

**Drill-down is read-only.** `/team/<code>/` reuses `_dashboard.html` with `own=False` (no "Open this week") plus that person's timesheets list; each week opens `/team/<code>/weeks/<YYYY-MM-DD>/`, which shows the rows, day summary and status with no edit, submit or approve controls (those stay on `/approvals/` and change requests). Access = `can_access_team` + `can_view` (403 otherwise; unknown code 404); a viewer may open their own drill-down.

## Consequences

- **Checked by:** [T-126](../testing.md#t-126), [T-130](../testing.md#t-130)
- **Cited in code:** [`apps/analytics/services/team.py`](../../apps/analytics/services/team.py), [`apps/analytics/views/team.py`](../../apps/analytics/views/team.py)
