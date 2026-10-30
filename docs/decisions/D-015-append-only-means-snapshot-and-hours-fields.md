# D-15: "Append-only" means snapshot and hours fields never change after creation

- **Status:** Accepted
- **Area:** Payroll
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Payroll** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.4 FR-11, B.5, B.6, B.9, B.10.

## Decision

"Append-only" means snapshot and hours fields never change after creation. Only `status`, `export_batch`, `exported_at`, `paid_at` and `superseded_at` may change, and only forward: CURRENT → EXPORTED → PAID, and any status → SUPERSEDED. Enforced in code and tested. *Extended by D-118 (SETTLED, `settled_at`) and D-120 (adjustments follow the same rules).*

## Consequences

- **Checked by:** [T-104](../testing.md#t-104)
- **Cited in code:** [`apps/payroll/admin.py`](../../apps/payroll/admin.py), [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/publish.py`](../../apps/payroll/services/publish.py), [`tests/payroll/integration/test_payroll_publish.py`](../../tests/payroll/integration/test_payroll_publish.py)
- **Related decisions:** [D-118](D-118-settled-weeks.md), [D-120](D-120-payrolladjustment.md)
