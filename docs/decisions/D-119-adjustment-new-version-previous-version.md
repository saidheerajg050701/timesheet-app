# D-119: Adjustment = new version − previous version

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 4 – Automatic pay adjustments (commit `fc2606b`)
- **Recorded:** 2026-10-25

## Context

A decision in the **Payroll** area, recorded during Change 4 – Automatic pay adjustments. It affects these parts of the specification: B.4 FR-11.

## Decision

**Adjustment = new version − previous version** of the week, separately for regular, overtime, PTO, sick, holiday and total minutes (signed). The previous version is the exported/paid one or an earlier settled one, so a week's adjustments always add up to "latest version − version first paid" and nothing is counted twice, also when an earlier adjustment has not been exported yet. A zero difference settles the week without an adjustment. Weeks whose earlier versions were never exported keep the old behaviour (new version CURRENT, exported normally).

## Consequences

- **Checked by:** [T-173](../testing.md#t-173), [T-174](../testing.md#t-174), [T-175](../testing.md#t-175), [T-176](../testing.md#t-176), [T-198](../testing.md#t-198)
- **Cited in code:** [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/adjustments.py`](../../apps/payroll/services/adjustments.py), [`apps/payroll/services/publish.py`](../../apps/payroll/services/publish.py), [`tests/payroll/integration/test_adjustments.py`](../../tests/payroll/integration/test_adjustments.py)
