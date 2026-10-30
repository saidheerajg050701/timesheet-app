# D-139: Change 9 – Managers decide every required person

- **Status:** Accepted
- **Area:** Approvals
- **From:** Change 9 – Managers decide everyone (commit `0f34b45`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Approvals** area, recorded during Change 9 – Managers decide everyone. It affects these parts of the specification: B.4 FR-7, D-11.

## Decision

**Change 9 – Managers decide every required person.** `decision_blockers` (one rule, used by the pages, approve, reject, edit and the pending view): every required week (D-56) must be **SUBMITTED or LOCKED**; a **REOPENED** week waits while the employee's window is open ("Week 1 is reopened until Fri Oct 23, 10:00 AM — waiting for Sara to resubmit"; no button to end it early) and becomes LOCKED — decidable — when the window ends unsubmitted; DRAFT / not started in a running week: "hasn't been submitted yet"; an open change request still blocks (D-58); an approved period: "already approved". **Approve** sets both weeks APPROVED with the hours entered (a locked week with no timesheet gets one), writes the PeriodApproval and publishes to payroll as before. **Reject** (comment required) reopens the required weeks per D-21, creating timesheets if needed; a resubmission makes it pending again (D-60). **Bulk approve** only clean rows: no locked week, no flags (D-63). Only the approver (direct manager; admins for no-manager staff, e.g. HR for the CEO), never oneself (403). Updates D-06, D-56, D-59.

## Consequences

- **Checked by:** [T-29](../testing.md#t-29), [T-218](../testing.md#t-218), [T-219](../testing.md#t-219), [T-220](../testing.md#t-220), [T-224](../testing.md#t-224)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/views/__init__.py`](../../apps/timesheets/views/__init__.py), [`tests/e2e/test_approvals.py`](../../tests/e2e/test_approvals.py), [`tests/timesheets/integration/test_approvals.py`](../../tests/timesheets/integration/test_approvals.py), [`tests/timesheets/integration/test_manager_decisions.py`](../../tests/timesheets/integration/test_manager_decisions.py)
- **Related decisions:** [D-06](D-006-only-submitted-weeks-can-be-approved.md), [D-21](D-021-reopen-window.md), [D-56](D-056-only-weeks-with-at-least-one-employed.md), [D-58](D-058-an-open-change-request-on-either-week.md), [D-59](D-059-unlock-on-the-approvals-page-reuses-phase.md), [D-60](D-060-resubmitting-a-week-of-a-rejected-period.md), [D-63](D-063-bulk-approve.md)
