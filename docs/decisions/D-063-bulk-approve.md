# D-63: Bulk approve

- **Status:** Accepted
- **Area:** Approvals
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Approvals** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-7.

## Decision

Bulk approve: only rows with the required weeks SUBMITTED, no flags, no open request and not yet decided can be ticked; the server re-checks every posted row, approves each employee in its own transaction and shows what was approved and what was skipped with reasons.

## Consequences

- **Checked by:** [T-96](../testing.md#t-96), [T-220](../testing.md#t-220)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/views/approvals.py`](../../apps/timesheets/views/approvals.py), [`tests/timesheets/integration/test_manager_decisions.py`](../../tests/timesheets/integration/test_manager_decisions.py)
