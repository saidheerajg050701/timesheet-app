# D-135: Finalize & export, Mark as paid, downloads

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 8 – Pay Period Register (commit `85f22e2`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Payroll** area, recorded during Change 8 – Pay Period Register. It affects these parts of the specification: B.4 FR-11, D-68.

## Decision

**Finalize & export, Mark as paid, downloads.** Finalize & export (READY only) runs in one payroll transaction: builds the lines, takes **one** new batch number (`EXP-`, also counting register batches), moves exactly the records the lines pay to EXPORTED in it, saves the register and lines; EXPORT audit row (entity `PayrollRegister`). It can't run twice for a period and never picks up an exported record again. **Mark as paid** moves the register and its batch's records to PAID once (PAY audit row). The old "Export CSV any time" button and the per-batch Mark as paid are **removed** — Finalize & export is the only action that creates a batch (`export_period` stays as an internal helper to build older-style data in tests). Finalized registers can be downloaded any number of times without changing anything: **Register CSV** `payroll-register_<start>_to_<end>_<batch>.csv` (the register columns, line status and carry_from; no totals row) and **Detailed CSV** `payroll-detail_…` (the WEEK / ADJUSTMENT format of D-123, unchanged); **Download all periods** `payroll-registers_<first>_to_<last>.csv` (period_start, period_end, batch + the register columns; optional from/to). Every text cell formula-safe (D-68); payroll staff and admins only. OPEN and READY periods have no download. *Updates D-68, D-69 and D-123.*

## Consequences

- **Checked by:** [T-37](../testing.md#t-37), [T-207](../testing.md#t-207), [T-211](../testing.md#t-211), [T-212](../testing.md#t-212), [T-216](../testing.md#t-216)
- **Cited in code:** [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/export.py`](../../apps/payroll/services/export.py), [`apps/payroll/services/register/__init__.py`](../../apps/payroll/services/register/__init__.py), [`apps/payroll/services/register/actions.py`](../../apps/payroll/services/register/actions.py), [`apps/payroll/services/register/constants.py`](../../apps/payroll/services/register/constants.py), [`apps/payroll/services/register/state.py`](../../apps/payroll/services/register/state.py), [`apps/payroll/services/register/table.py`](../../apps/payroll/services/register/table.py), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`tests/e2e/test_payroll.py`](../../tests/e2e/test_payroll.py), [`tests/payroll/integration/test_payroll_pages.py`](../../tests/payroll/integration/test_payroll_pages.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py)
- **Related decisions:** [D-68](D-068-export-csv-covers-all-current-records-of.md), [D-69](D-069-mark-as-paid-works-per-batch.md), [D-123](D-123-export-csv-mark-as-paid.md)
