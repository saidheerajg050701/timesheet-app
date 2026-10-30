# D-118: Change 4 – settled weeks

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 4 – Automatic pay adjustments (commit `fc2606b`)
- **Recorded:** 2026-10-25

## Context

A decision in the **Payroll** area, recorded during Change 4 – Automatic pay adjustments. It affects these parts of the specification: B.4 FR-11, B.5, D-15.

## Decision

**Change 4 – settled weeks.** `PayrollWeek` gains status **SETTLED** ("a corrected version paid through the original payment plus adjustments; never exported as a week row") and lifecycle field `settled_at`. New moves: CURRENT → SETTLED, SETTLED → SUPERSEDED; new records still start CURRENT; a SETTLED record is the week's live record (D-66). Rule: once any version of an employee-week has been exported (`exported_at` set), every later version is settled as it is published.

## Consequences

- **Checked by:** [T-173](../testing.md#t-173), [T-177](../testing.md#t-177), [T-198](../testing.md#t-198)
- **Cited in code:** [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/adjustments.py`](../../apps/payroll/services/adjustments.py), [`apps/payroll/services/export.py`](../../apps/payroll/services/export.py), [`apps/payroll/services/publish.py`](../../apps/payroll/services/publish.py), [`apps/timesheets/templatetags/timesheet_tags.py`](../../apps/timesheets/templatetags/timesheet_tags.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py), [`tests/payroll/integration/test_adjustments.py`](../../tests/payroll/integration/test_adjustments.py)
- **Related decisions:** [D-66](D-066-a-payroll-record-belongs-to-one-approval.md)
