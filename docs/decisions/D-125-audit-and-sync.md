# D-125: Audit and sync

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 4 – Automatic pay adjustments (commit `fc2606b`)
- **Recorded:** 2026-10-25

## Context

A decision in the **Payroll** area, recorded during Change 4 – Automatic pay adjustments. It affects these parts of the specification: B.9 #13, D-22, D-65.

## Decision

**Audit and sync**: adjustments are created in the same after-commit payroll transaction as the settled version (D-65). Audit reuses existing actions (no change to `AuditLog.Action` or the main database): **PUBLISH** with entity `PayrollAdjustment` (approver or system actor; versions, amounts, period; no reason); the batch **EXPORT**/**PAY** rows add `adjustments` when the batch has any. `sync_payroll` also settles live CURRENT versions of once-exported weeks and creates missing adjustments, idempotently; its SYNC row reports `adjustments`; `sync_payroll()` still returns (published, superseded).

## Consequences

- **Checked by:** [T-180](../testing.md#t-180), [T-181](../testing.md#t-181)
- **Cited in code:** [`apps/payroll/services/adjustments.py`](../../apps/payroll/services/adjustments.py), [`apps/payroll/services/export.py`](../../apps/payroll/services/export.py), [`apps/payroll/services/publish.py`](../../apps/payroll/services/publish.py), [`apps/payroll/services/sync.py`](../../apps/payroll/services/sync.py), [`tests/payroll/integration/test_adjustments.py`](../../tests/payroll/integration/test_adjustments.py)
- **Related decisions:** [D-65](D-065-two-databases-fixed-order.md)
