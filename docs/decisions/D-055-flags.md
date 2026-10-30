# D-55: Flags

- **Status:** Accepted
- **Area:** Approvals
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Approvals** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-7.

## Decision

Flags: **late** = either week `is_late`; **overtime** = a week's Hours worked (Phase 5b `summarize`, Break excluded) above that week's prorated expected hours; **missing days** = an employed weekday (Mon–Fri, up to today) with no entries at all (leave counts as an entry).

## Consequences

- **Checked by:** [T-98](../testing.md#t-98)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`tests/timesheets/integration/test_approvals.py`](../../tests/timesheets/integration/test_approvals.py)
