# D-95: E2E is mandatory

- **Status:** Accepted
- **Area:** Tests
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Tests** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.11, D-01.

## Decision

**E2E is mandatory**: `test_all.sh` step 5 runs `uv run pytest -m e2e` and fails on any non-zero exit code, including 5 ("no tests collected"); this ends the D-01 skip rule. Chromium is installed once by the owner (`uv run playwright install chromium`). Extra script arguments are passed to this step (e.g. `--browser-channel chrome`).

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`scripts/test_all.sh`](../../scripts/test_all.sh)
- **Related decisions:** [D-01](D-001-test-all-sh.md)
