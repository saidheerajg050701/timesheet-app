# D-68: Export CSV covers all CURRENT records of the selected period (filters only change the…

- **Status:** Accepted
- **Area:** Payroll
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Payroll** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-11.

## Decision

Export CSV covers **all CURRENT records of the selected period** (filters only change the view) as one batch numbered `EXP-0001`, `EXP-0002`, …; a batch can be downloaded again without changing anything; every cell starting with `=`, `+`, `-`, `@`, tab or CR gets a leading `'` so Excel/Numbers never run it as a formula. *Extended by D-123: the batch also holds the period's adjustments; hour columns are app-made numbers written as is, text cells stay formula-safe.* *Since D-135 only Finalize & export creates a batch, one per register.*

## Consequences

- **Checked by:** [T-110](../testing.md#t-110), [T-212](../testing.md#t-212)
- **Cited in code:** [`apps/directory/services/directory_admin.py`](../../apps/directory/services/directory_admin.py), [`apps/payroll/services/export.py`](../../apps/payroll/services/export.py), [`apps/payroll/services/register/table.py`](../../apps/payroll/services/register/table.py), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`apps/reports/services/cost_files.py`](../../apps/reports/services/cost_files.py), [`apps/reports/services/report_files.py`](../../apps/reports/services/report_files.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py)
- **Related decisions:** [D-123](D-123-export-csv-mark-as-paid.md), [D-135](D-135-finalize-export-mark-as-paid-downloads.md)
