# D-121: Carry-forward period

- **Status:** Accepted — later updated by D-136
- **Area:** Payroll
- **From:** Change 4 – Automatic pay adjustments (commit `fc2606b`)
- **Recorded:** 2026-10-25

## Context

A decision in the **Payroll** area, recorded during Change 4 – Automatic pay adjustments. It affects these parts of the specification: B.4 FR-11.

## Decision

**Carry-forward period**: from the later of (the period after the corrected week's own period) and (the most recent completed period at re-approval, `default_period(at)`), the first period — stepping 14 days — that has no export batch yet (no exported week record or adjustment). That period's next export includes the adjustment. *Since D-136 a period also counts as exported when its register is finalized.*

## Consequences

- **Checked by:** [T-173](../testing.md#t-173), [T-178](../testing.md#t-178), [T-198](../testing.md#t-198)
- **Cited in code:** [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/adjustments.py`](../../apps/payroll/services/adjustments.py), [`apps/payroll/services/publish.py`](../../apps/payroll/services/publish.py), [`apps/payroll/services/register/state.py`](../../apps/payroll/services/register/state.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py), [`tests/payroll/integration/test_adjustments.py`](../../tests/payroll/integration/test_adjustments.py)
- **Related decisions:** [D-136](D-136-carry-forward-with-registers.md)
- **Updated later by:** [D-136](D-136-carry-forward-with-registers.md)
