# D-132: Change 8 – Pay Period Register

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 8 – Pay Period Register (commit `85f22e2`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Payroll** area, recorded during Change 8 – Pay Period Register. It affects these parts of the specification: B.4 FR-11, B.6, D-15.

## Decision

**Change 8 – Pay Period Register.** Every ended 2-week pay period has a register. While it isn't finalized it is **worked out live** (status **OPEN**, then **READY**) — never saved, because an approval can still go back to PENDING when an approved week is edited or unlocked, and payroll records only move forward. **Finalize & export** saves it as `PayrollRegister` (payroll database only, append-only through `AppendOnlyRecord`: born **FINALIZED** with its batch, who finalized it and when, why it was ready, approved x of y; the only move is FINALIZED → **PAID**, setting `paid_at`) with one `PayrollRegisterLine` per employee (`FrozenRecord`: saved once, never changed or deleted; a foreign key to its register inside the payroll database, none across databases). Migration `payroll/0003`; no change to `db.sqlite3`.

## Consequences

- **Checked by:** [T-210](../testing.md#t-210), [T-216](../testing.md#t-216)
- **Cited in code:** [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/register/__init__.py`](../../apps/payroll/services/register/__init__.py), [`apps/payroll/services/register/constants.py`](../../apps/payroll/services/register/constants.py), [`apps/payroll/services/register/state.py`](../../apps/payroll/services/register/state.py), [`apps/payroll/templates/payroll/_register_status.html`](../../apps/payroll/templates/payroll/_register_status.html), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`apps/timesheets/templatetags/timesheet_tags.py`](../../apps/timesheets/templatetags/timesheet_tags.py), [`tests/e2e/test_payroll.py`](../../tests/e2e/test_payroll.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py)
