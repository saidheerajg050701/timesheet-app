# D-58: An open change request on either week blocks Approve and Reject (and bulk approve…

- **Status:** Accepted
- **Area:** Approvals
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Approvals** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-7/FR-9.

## Decision

An open change request on either week blocks Approve and Reject (and bulk approve skips the row) until it is handled.

## Consequences

- **Checked by:** [T-101](../testing.md#t-101)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`tests/timesheets/integration/test_approvals.py`](../../tests/timesheets/integration/test_approvals.py)
