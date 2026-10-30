# D-123: Export, CSV, Mark as paid

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 4 – Automatic pay adjustments (commit `fc2606b`)
- **Recorded:** 2026-10-25

## Context

A decision in the **Payroll** area, recorded during Change 4 – Automatic pay adjustments. It affects these parts of the specification: B.4 FR-11, D-68, D-69.

## Decision

**Export, CSV, Mark as paid**: Export CSV takes the period's CURRENT week records and CURRENT adjustments into one batch (shared `EXP-` numbering); SETTLED weeks are never exported. CSV columns: `batch, employee_code, row_type (WEEK/ADJUSTMENT), …, week_start` (blank for adjustments), `original_week` (adjustments), hours, `version` (`1→2` for adjustments), `status`; per employee, week rows first. Hour columns are numbers the app computes and are written as is (adjustments may be `-1.50`); every text cell still goes through `safe_cell` (D-68). Mark as paid pays the batch's records and adjustments. *The detailed CSV is unchanged; since D-135 it is downloaded per register.*

## Consequences

- **Checked by:** [T-174](../testing.md#t-174), [T-177](../testing.md#t-177), [T-179](../testing.md#t-179)
- **Cited in code:** [`apps/payroll/services/export.py`](../../apps/payroll/services/export.py), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`tests/payroll/integration/test_adjustments.py`](../../tests/payroll/integration/test_adjustments.py)
- **Related decisions:** [D-68](D-068-export-csv-covers-all-current-records-of.md), [D-135](D-135-finalize-export-mark-as-paid-downloads.md)
