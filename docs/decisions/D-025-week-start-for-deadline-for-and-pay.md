# D-25: week_start_for, deadline_for and pay_period_for are built in Phase 2 (seed_demo needs…

- **Status:** Accepted
- **Area:** Setup
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Setup** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.9, C.4 P2/P5.

## Decision

`week_start_for`, `deadline_for` and `pay_period_for` are built in Phase 2 (seed_demo needs them), with tests T-12, T-15 and T-16. Phase 5 adds `effective_status`, `expected_minutes_for` and the other calendar tests.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py)
