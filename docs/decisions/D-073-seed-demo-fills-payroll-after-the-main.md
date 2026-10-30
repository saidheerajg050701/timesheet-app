# D-73: seed_demo fills payroll after the main seed commits (publish every approved period

- **Status:** Accepted — later updated by D-137
- **Area:** Data
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Data** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.7.

## Decision

`seed_demo` fills payroll after the main seed commits (publish every approved period; oldest periods EXPORTED and PAID, next EXPORTED, newest CURRENT; one correction). If the payroll part fails, the main data stays and `sync_payroll` completes it; seed_demo still refuses when data exists.

## Consequences

- **Checked by:** [T-114](../testing.md#t-114)
- **Cited in code:** [`apps/directory/services/demo/__init__.py`](../../apps/directory/services/demo/__init__.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py)
- **Updated later by:** [D-137](D-137-earlier-data-sync-seed.md)
