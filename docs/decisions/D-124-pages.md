# D-124: Pages

- **Status:** Accepted — later updated by D-138
- **Area:** Payroll
- **From:** Change 4 – Automatic pay adjustments (commit `fc2606b`)
- **Recorded:** 2026-10-25

## Context

A decision in the **Payroll** area, recorded during Change 4 – Automatic pay adjustments. It affects these parts of the specification: B.4 FR-11, B.8.

## Decision

**Pages**: Payroll totals keep the week columns (each week's current approved hours, settled weeks included), add **Adjustments** (carried into this period) and **Total = weeks + adjustments**; a table "Adjustments carried to this period" (same filters); the period list includes periods with only adjustments; the export button counts both. **Corrections** (replaces D-70): one row per version change of a week that had been exported or settled — old version (Paid/Exported with batch, or Settled), new version, difference, the adjustment with its period and status (**Scheduled**, **Exported in EXP-xxxx**, **Paid**), the reason; "waiting for re-approval" before re-approval and "no adjustment (0.00)" for a zero difference. *Follow-up:* in a period's week records, each Settled week shows "Settled by adjustment in <period>" linking to the period its adjustment was carried to, or "No difference to pay" for a zero difference (T-182). *Replaced by D-138 (pay period list and register page).*

## Consequences

- **Checked by:** [T-179](../testing.md#t-179), [T-182](../testing.md#t-182)
- **Cited in code:** [`apps/payroll/services/export.py`](../../apps/payroll/services/export.py), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`tests/payroll/integration/test_adjustments.py`](../../tests/payroll/integration/test_adjustments.py)
- **Related decisions:** [D-70](D-070-corrections-superseded-records-that-had-been-exported.md), [D-138](D-138-pages.md)
- **Updated later by:** [D-138](D-138-pages.md)
