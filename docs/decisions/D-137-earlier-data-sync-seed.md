# D-137: Earlier data, sync, seed

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 8 – Pay Period Register (commit `85f22e2`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Payroll** area, recorded during Change 8 – Pay Period Register. It affects these parts of the specification: B.7, D-65, D-73 *Seed updated by D-144.*.

## Decision

**Earlier data, sync, seed.** `manage.py build_registers` (idempotent) gives every period that already has export batches a FINALIZED register — its batch, or several joined with `+` — built from exactly what was exported (no 0.00 lines), PAID when those batches were paid; leftover CURRENT weeks there become late approvals (D-136); PUBLISH audit row per register (system actor). `sync_payroll` runs the same step and reports `registers`; the out-of-sync banner also counts exported periods without a register. `seed_demo` finalizes & exports the older approved periods' registers through the real flow (their deadlines have passed) and pays all but the newest of them (updates D-73, D-126).

## Consequences

- **Checked by:** [T-114](../testing.md#t-114), [T-214](../testing.md#t-214), [T-215](../testing.md#t-215)
- **Cited in code:** [`apps/directory/services/demo/payroll.py`](../../apps/directory/services/demo/payroll.py), [`apps/payroll/management/commands/build_registers.py`](../../apps/payroll/management/commands/build_registers.py), [`apps/payroll/services/register/__init__.py`](../../apps/payroll/services/register/__init__.py), [`apps/payroll/services/register/backfill.py`](../../apps/payroll/services/register/backfill.py), [`apps/payroll/services/sync.py`](../../apps/payroll/services/sync.py), [`apps/payroll/templates/payroll/_out_of_sync.html`](../../apps/payroll/templates/payroll/_out_of_sync.html), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py)
- **Related decisions:** [D-73](D-073-seed-demo-fills-payroll-after-the-main.md), [D-126](D-126-seed.md), [D-136](D-136-carry-forward-with-registers.md)
