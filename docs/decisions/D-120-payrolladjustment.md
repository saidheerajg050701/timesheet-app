# D-120: PayrollAdjustment

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 4 – Automatic pay adjustments (commit `fc2606b`)
- **Recorded:** 2026-10-25

## Context

A decision in the **Payroll** area, recorded during Change 4 – Automatic pay adjustments. It affects these parts of the specification: B.6, D-15, D-67.

## Decision

**`PayrollAdjustment`** (payroll database only, append-only like D-15 through the shared `AppendOnlyRecord` base): frozen employee snapshot, the corrected week and its period, the period it is carried to, old and new version, the six signed amounts, approver and approval time, reason and source timesheet id; status CURRENT → EXPORTED → PAID with `export_batch`, `exported_at`, `paid_at`; one per (employee, week, new version). Schema migration `payroll/0002` (payroll database only).

## Consequences

- **Checked by:** [T-181](../testing.md#t-181), [T-198](../testing.md#t-198)
- **Cited in code:** [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/adjustments.py`](../../apps/payroll/services/adjustments.py), [`apps/payroll/services/publish.py`](../../apps/payroll/services/publish.py), [`tests/payroll/integration/test_adjustments.py`](../../tests/payroll/integration/test_adjustments.py)
- **Related decisions:** [D-15](D-015-append-only-means-snapshot-and-hours-fields.md)
