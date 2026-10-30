# D-57: Reject has the same precondition as Approve and needs a comment

- **Status:** Accepted
- **Area:** Approvals
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Approvals** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-7, B.5.

## Decision

Reject has the same precondition as Approve and needs a comment; the required weeks become REOPENED with `reopen_until` per D-21 (D-07); the comment is stored on the PeriodApproval and as `manager_note` on the weeks.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py)
- **Related decisions:** [D-07](D-007-reject-sets-both-weeks-to-reopened-with.md), [D-21](D-021-reopen-window.md)
