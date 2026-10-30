# D-30: Menu items for pages built in later phases (Timesheets, Requests, Team, Approvals,…

- **Status:** Accepted
- **Area:** Layout
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Layout** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.8, C.4 P4–P10.

## Decision

Menu items for pages built in later phases (Timesheets, Requests, Team, Approvals, Payroll) link to simple "coming in a later phase" placeholder pages that already enforce the correct permission on the server, so menus and 403s can be tested from Phase 4. Later phases replace the views but keep the URLs and URL names.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/analytics/urls.py`](../../apps/analytics/urls.py), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py)
