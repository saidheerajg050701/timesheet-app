# D-136: Carry-forward with registers

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 8 – Pay Period Register (commit `85f22e2`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Payroll** area, recorded during Change 8 – Pay Period Register. It affects these parts of the specification: B.4 FR-11.

## Decision

**Carry-forward with registers** (updates D-121). A period is **closed** when its register is finalized or paid — or, for data from before registers, when it has an export batch. `carry_period` still starts from the later of the period after the corrected week and the most recent completed period, and takes the first one that isn't closed; so a correction to a week of a finalized or paid register is paid in the next register that isn't finalized. **Late approvals:** weeks approved after their own register was finalized (their people had a 0.00 line) stay CURRENT and are carried into the first not-closed period after their own, as carry-forward with their original weeks, and exported with that register — once. CURRENT adjustments left in a closed period are carried the same way.

## Consequences

- **Checked by:** [T-37](../testing.md#t-37), [T-208](../testing.md#t-208), [T-209](../testing.md#t-209)
- **Cited in code:** [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/adjustments.py`](../../apps/payroll/services/adjustments.py), [`apps/payroll/services/export.py`](../../apps/payroll/services/export.py), [`apps/payroll/services/register/__init__.py`](../../apps/payroll/services/register/__init__.py), [`apps/payroll/services/register/constants.py`](../../apps/payroll/services/register/constants.py), [`apps/payroll/services/register/state.py`](../../apps/payroll/services/register/state.py), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`tests/payroll/integration/test_payroll_pages.py`](../../tests/payroll/integration/test_payroll_pages.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py)
- **Related decisions:** [D-121](D-121-carry-forward-period.md)
