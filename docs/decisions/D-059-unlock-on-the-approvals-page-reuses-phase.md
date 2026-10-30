# D-59: Unlock on the approvals page reuses Phase 6 approvals.unlock_week

- **Status:** Accepted
- **Area:** Approvals
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Approvals** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-7, D-06 *Unlock stays; since D-139/D-140 the approver can also edit and decide a locked week directly.*.

## Decision

Unlock on the approvals page reuses Phase 6 `approvals.unlock_week`: it resolves the employee's open request on that week if there is one, otherwise records a manager-authored ChangeRequest (requester = manager, UNLOCKED); a missed week with no timesheet is created as LOCKED first. Audited.

## Consequences

- **Checked by:** [T-92](../testing.md#t-92)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py)
