# D-56: Only weeks with at least one employed day must be SUBMITTED; a week fully outside…

- **Status:** Accepted
- **Area:** Approvals
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Approvals** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-7, B.5 *Since D-139 a required week must be SUBMITTED or LOCKED.*.

## Decision

Only weeks with at least one employed day must be SUBMITTED; a week fully outside employment is not required (refines D-06 for D-19).

## Consequences

- **Checked by:** [T-100](../testing.md#t-100)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py)
- **Related decisions:** [D-06](D-006-only-submitted-weeks-can-be-approved.md), [D-19](D-019-add-employee-end-date-nullable-set-on.md)
