# D-122: Reason

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 4 – Automatic pay adjustments (commit `fc2606b`)
- **Recorded:** 2026-10-25

## Context

A decision in the **Payroll** area, recorded during Change 4 – Automatic pay adjustments. It affects these parts of the specification: B.4 FR-11, D-12.

## Decision

**Reason** = the reason of the latest handled change request (Edit directly or Unlock, including the manager-authored unlock from Approvals) on the week's timesheet, otherwise "Re-approved after a change". Stored on the adjustment and shown **only on the Corrections page** — never in the CSV, on the Payroll page or in the audit summary (D-12).

## Consequences

- **Checked by:** [T-173](../testing.md#t-173), [T-179](../testing.md#t-179), [T-198](../testing.md#t-198)
- **Cited in code:** [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/adjustments.py`](../../apps/payroll/services/adjustments.py), [`apps/payroll/services/register/__init__.py`](../../apps/payroll/services/register/__init__.py), [`tests/payroll/integration/test_adjustments.py`](../../tests/payroll/integration/test_adjustments.py)
- **Related decisions:** [D-12](D-012-roles-add-up.md)
