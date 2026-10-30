# D-146: seed_demo refuses the example DEMO_PASSWORD

- **Status:** Accepted
- **Area:** Setup
- **From:** README & first-run checks (commit `e17cc7d`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Setup** area, recorded during README & first-run checks. It affects these parts of the specification: B.7.

## Decision

**`seed_demo` refuses the example `DEMO_PASSWORD`** (`choose-a-strong-demo-password` from `.env.example`) with a clear message, before anything is written — in addition to the empty and weak-password checks.

## Consequences

- **Checked by:** [T-226](../testing.md#t-226)
- **Cited in code:** [`apps/directory/management/commands/seed_demo.py`](../../apps/directory/management/commands/seed_demo.py), [`tests/site/test_first_run_checks.py`](../../tests/site/test_first_run_checks.py)
