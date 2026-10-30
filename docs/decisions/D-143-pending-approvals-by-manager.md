# D-143: Pending approvals by manager

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 9 – Managers decide everyone (commit `0f34b45`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Payroll** area, recorded during Change 9 – Managers decide everyone. It affects these parts of the specification: B.4 FR-11, D-12.

## Decision

**Pending approvals by manager** (`/payroll/pending/`, payroll staff and admins; read only — nobody approves there): for a period (default the most recent ended one) one row per approver who still has people to approve — manager and team ("HR / admins" for no-manager staff), pending x of y, each person with their state (Submitted, Locked – not submitted, Reopened until …, Change request open, Not submitted yet) and Overdue after the deadline; totals managers done x of y and people approved x of y; CSV `payroll-pending_<start>_to_<end>.csv` (formula-safe). Linked from the Payroll list ("Who's pending" on OPEN periods), the register page and the Admin header. Built from `company_period_rows` + `decision_blockers` (one rule).

## Consequences

- **Checked by:** [T-223](../testing.md#t-223)
- **Cited in code:** [`apps/payroll/templates/payroll/_pending_groups.html`](../../apps/payroll/templates/payroll/_pending_groups.html), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/pending.py`](../../apps/timesheets/services/pending.py), [`tests/timesheets/integration/test_manager_decisions.py`](../../tests/timesheets/integration/test_manager_decisions.py)
