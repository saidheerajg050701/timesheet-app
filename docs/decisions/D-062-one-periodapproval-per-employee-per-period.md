# D-62: One PeriodApproval per employee per period

- **Status:** Accepted
- **Area:** Data
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Data** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.6.

## Decision

One PeriodApproval per employee per period: unique constraint `one_approval_per_period` (migration `timesheets/0004`).

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py)
