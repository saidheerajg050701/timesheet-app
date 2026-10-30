# D-138: Pages

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 8 – Pay Period Register (commit `85f22e2`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Payroll** area, recorded during Change 8 – Pay Period Register. It affects these parts of the specification: B.4 FR-11, D-124.

## Decision

**Pages.** `/payroll/` lists every ended pay period newest first: dates, status (Open, Ready, Finalized & exported, Paid), approved x of y, pay total, batch and the two downloads once finalized, plus "Download all periods"; older `?period=` links redirect to the period page. `/payroll/periods/<start>/`: status, approval deadline, the register (live preview or saved lines; carry-forward columns highlighted; totals row), the "Not approved yet" list, Finalize & export (confirmed in an in-page dialog) or the downloads and Mark as paid, then the week records and adjustments with their filters. **Corrections** links each adjustment to the register that pays it, with that register's status (updates D-124).

## Consequences

- **Checked by:** [T-213](../testing.md#t-213)
- **Cited in code:** [`apps/payroll/services/export.py`](../../apps/payroll/services/export.py), [`apps/payroll/services/register/table.py`](../../apps/payroll/services/register/table.py), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py)
- **Related decisions:** [D-124](D-124-pages.md)
