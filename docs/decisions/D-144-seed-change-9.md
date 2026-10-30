# D-144: Seed (Change 9)

- **Status:** Accepted
- **Area:** Data
- **From:** Change 9 – Managers decide everyone (commit `0f34b45`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Data** area, recorded during Change 9 – Managers decide everyone. It affects these parts of the specification: B.7.

## Decision

**Seed (Change 9):** after the history is built, each manager also approves the people older periods left pending — locked weeks with what was entered, and weeks with no timesheet (sign-up candidates) at 0.00 — through `approve_period`, so every older period is fully approved and its register can be finalized; those weeks keep no submission time (still missed). The most recent completed period stays pending (B.7). Updates D-137.

## Consequences

- **Checked by:** [T-41](../testing.md#t-41), [T-114](../testing.md#t-114)
- **Cited in code:** [`apps/directory/services/demo/payroll.py`](../../apps/directory/services/demo/payroll.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py)
- **Related decisions:** [D-137](D-137-earlier-data-sync-seed.md)
