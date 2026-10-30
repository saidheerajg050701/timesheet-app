# D-06: Only SUBMITTED weeks can be approved

- **Status:** Accepted — later updated by D-56
- **Area:** Timesheet status
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Timesheet status** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.1, B.4 FR-7, B.5, B.6, B.7, B.8, B.9, B.11 T-29 *Since D-139 a LOCKED week no longer has to be unlocked first: the approver can edit, approve or reject it from Approvals.*.

## Decision

Only SUBMITTED weeks can be approved. A LOCKED week must first be unlocked (through a change request, or by the manager directly from the approval page, which creates a manager-authored ChangeRequest and an audit entry) and then submitted.

## Consequences

- **Checked by:** [T-56](../testing.md#t-56), [T-92](../testing.md#t-92)
- **Cited in code:** [`apps/directory/services/demo/approvals.py`](../../apps/directory/services/demo/approvals.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py)
- **Updated later by:** [D-56](D-056-only-weeks-with-at-least-one-employed.md)
