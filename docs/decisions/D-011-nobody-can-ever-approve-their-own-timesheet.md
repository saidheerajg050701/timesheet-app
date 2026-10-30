# D-11: Nobody can ever approve their own timesheet

- **Status:** Accepted
- **Area:** Roles
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Roles** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.1, B.3, B.4 FR-7, B.9.

## Decision

Nobody can ever approve their own timesheet. Approver = direct manager. Admins approve only employees with no manager, never themselves (the CEO is approved by the HR admin). In B.3, Admin approves "top-level employees only".

## Consequences

- **Checked by:** [T-56](../testing.md#t-56), [T-60](../testing.md#t-60), [T-61](../testing.md#t-61), [T-95](../testing.md#t-95), [T-221](../testing.md#t-221)
- **Cited in code:** [`apps/directory/services/demo/approvals.py`](../../apps/directory/services/demo/approvals.py), [`apps/directory/services/demo/payroll.py`](../../apps/directory/services/demo/payroll.py), [`apps/directory/services/permissions.py`](../../apps/directory/services/permissions.py), [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py), [`apps/timesheets/services/pending.py`](../../apps/timesheets/services/pending.py), [`apps/timesheets/views/approvals.py`](../../apps/timesheets/views/approvals.py), [`apps/timesheets/views/requests.py`](../../apps/timesheets/views/requests.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py), [`tests/e2e/test_payroll.py`](../../tests/e2e/test_payroll.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py), [`tests/timesheets/integration/test_manager_decisions.py`](../../tests/timesheets/integration/test_manager_decisions.py)
