# D-134: Register lines

- **Status:** Accepted — later updated by D-142
- **Area:** Payroll
- **From:** Change 8 – Pay Period Register (commit `85f22e2`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Payroll** area, recorded during Change 8 – Pay Period Register. It affects these parts of the specification: B.4 FR-11, D-12, D-54 *Since D-142 there are no 0.00 lines: a register is finalized only with everyone approved; the two statuses remain only on registers saved before.*.

## Decision

**Register lines.** One line for each person who must be approved in the period — the approvals rule (D-54), now one shared function `must_be_approved`, company-wide — and one for anyone else with something to pay. Columns: code, name, department, team, approver and approval time; Week 1 and Week 2 regular, overtime, PTO, sick, holiday; Period (their sums) and Period total; Carry-forward in (regular, overtime, PTO, sick, holiday, Carry total, signed) and the original weeks they came from; **Pay total = Period total + Carry total**; a totals row on screen. Every number comes from PayrollWeek and PayrollAdjustment records (`split_hours`, so Break is never paid); nothing is worked out a second way. **Line status:** Approved; **Missed – not submitted** (a required week not submitted) or **Waiting for manager approval** (submitted, not approved) — both 0.00, read from the approvals data, timesheets never changed; **Carry-forward only**. The page lists the people still pending with their approver (manager, or "HR / an admin") and why.

## Consequences

- **Checked by:** [T-204](../testing.md#t-204), [T-206](../testing.md#t-206), [T-216](../testing.md#t-216)
- **Cited in code:** [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/register/__init__.py`](../../apps/payroll/services/register/__init__.py), [`apps/payroll/services/register/constants.py`](../../apps/payroll/services/register/constants.py), [`apps/payroll/services/register/state.py`](../../apps/payroll/services/register/state.py), [`apps/payroll/services/register/table.py`](../../apps/payroll/services/register/table.py), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/e2e/test_payroll.py`](../../tests/e2e/test_payroll.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py)
- **Related decisions:** [D-54](D-054-approvals-lists-the-employees-the-viewer-may.md)
- **Updated later by:** [D-142](D-142-the-register-waits-for-everyone.md)
