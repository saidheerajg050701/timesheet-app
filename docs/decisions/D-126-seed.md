# D-126: Seed

- **Status:** Accepted
- **Area:** Data
- **From:** Change 4 – Automatic pay adjustments (commit `fc2606b`)
- **Recorded:** 2026-10-25

## Context

A decision in the **Data** area, recorded during Change 4 – Automatic pay adjustments. It affects these parts of the specification: B.7, T-114.

## Decision

**Seed**: the existing correction (an hour added to a paid week of the oldest period) now publishes its v2 as SETTLED with a **+1.00 h adjustment, Scheduled**, carried to the first period without an export batch (the last approved period, whose weeks are still waiting to be exported) — one correction plus one carried-forward adjustment.

## Consequences

- **Checked by:** [T-114](../testing.md#t-114)
- **Cited in code:** [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py), [`tests/payroll/integration/test_adjustments.py`](../../tests/payroll/integration/test_adjustments.py)
