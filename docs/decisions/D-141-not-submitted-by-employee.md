# D-141: "Not submitted by employee"

- **Status:** Accepted
- **Area:** Approvals
- **From:** Change 9 – Managers decide everyone (commit `0f34b45`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Approvals** area, recorded during Change 9 – Managers decide everyone. It affects these parts of the specification: B.4 FR-7, D-75.

## Decision

**"Not submitted by employee"** = a required LOCKED or APPROVED week with no submission time (`submitted_at` empty) — the same fact that makes it **missed** (D-75), so dashboards and team analytics keep counting it as missed after approval, and **no migration** is needed. Shown on the Approvals row and period page, on the edit page and on the employee's week ("Approved by your manager without your submission"); the APPROVE audit row lists `not_submitted_by_employee`. Approving with a LOCKED week needs an explicit confirmation (in-page dialog; refused on the server without it) listing "Week N was not submitted by …; it will be approved with X.XX hours" and warnings for 0.00 hours and missing days.

## Consequences

- **Checked by:** [T-29](../testing.md#t-29), [T-217](../testing.md#t-217), [T-218](../testing.md#t-218), [T-224](../testing.md#t-224)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py), [`apps/timesheets/templatetags/timesheet_tags.py`](../../apps/timesheets/templatetags/timesheet_tags.py), [`tests/e2e/test_approvals.py`](../../tests/e2e/test_approvals.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py), [`tests/timesheets/integration/test_approvals.py`](../../tests/timesheets/integration/test_approvals.py), [`tests/timesheets/integration/test_manager_decisions.py`](../../tests/timesheets/integration/test_manager_decisions.py)
- **Related decisions:** [D-75](D-075-a-week-counts-when-its-deadline-has.md)
