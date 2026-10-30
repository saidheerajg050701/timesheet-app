# D-79: The dashboard is built by apps/analytics/services/metrics.py → dashboard_for(employee,…

- **Status:** Accepted
- **Area:** Analytics
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Analytics** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: C.4 P9/P10.

## Decision

The dashboard is built by `apps/analytics/services/metrics.py → dashboard_for(employee, weeks, now)` and rendered by `apps/analytics/templates/analytics/_dashboard.html` plus `parts/*.html`, which take that object (and `own`) — Phase 10 reuses them read-only for a team member.

*Paths updated in Refactor R3 to the app layout of Refactor R2 ([D-174](D-174-refactor-r2-own-apps-everything-in-apps.md)); nothing else changed.*

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/analytics/templates/analytics/_dashboard.html`](../../apps/analytics/templates/analytics/_dashboard.html), [`apps/analytics/views/dashboard.py`](../../apps/analytics/views/dashboard.py)
