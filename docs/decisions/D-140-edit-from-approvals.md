# D-140: Edit from Approvals

- **Status:** Accepted
- **Area:** Approvals
- **From:** Change 9 – Managers decide everyone (commit `0f34b45`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Approvals** area, recorded during Change 9 – Managers decide everyone. It affects these parts of the specification: B.4 FR-7, D-49.

## Decision

**Edit from Approvals** (`changes.edit_for_approval`, no change request): the approver opens a SUBMITTED or LOCKED week of a not-yet-approved period in the weekly grid (time slots, Break, leave, ⋮ row menu, optional reason, live day summary), pre-filled with what the employee entered or empty, and saves. Same validation as everywhere (`validate_entries`; submission rules only for a submitted week). The week keeps its status and its submission time — the manager's edit is never the employee's submission (unlike Edit directly, D-52). UPDATE audit row with before/after entries, the actor and `"via": "approvals"`. Refused while REOPENED, with an open change request, outside employment, once the period is approved (corrections then go through change requests) and for anyone the viewer doesn't approve.

## Consequences

- **Checked by:** [T-217](../testing.md#t-217), [T-220](../testing.md#t-220), [T-224](../testing.md#t-224), [T-231](../testing.md#t-231)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py), [`apps/timesheets/views/approvals.py`](../../apps/timesheets/views/approvals.py), [`tests/e2e/test_approvals.py`](../../tests/e2e/test_approvals.py), [`tests/timesheets/integration/test_manager_decisions.py`](../../tests/timesheets/integration/test_manager_decisions.py)
- **Related decisions:** [D-52](D-052-is-late-is-decided-by-the-first.md)
