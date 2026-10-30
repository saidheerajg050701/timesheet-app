# D-69: Mark as paid works per batch

- **Status:** Accepted
- **Area:** Payroll
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Payroll** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-11.

## Decision

Mark as paid works per batch: its EXPORTED records become PAID (`paid_at`); anything else in the batch (e.g. superseded) is untouched. *Extended by D-123: adjustments in the batch are paid too.*

## Consequences

- **Checked by:** [T-112](../testing.md#t-112)
- **Cited in code:** [`apps/payroll/services/export.py`](../../apps/payroll/services/export.py)
- **Related decisions:** [D-123](D-123-export-csv-mark-as-paid.md)
