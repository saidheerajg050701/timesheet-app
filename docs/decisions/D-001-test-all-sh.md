# D-01: test_all.sh

- **Status:** Accepted
- **Area:** Setup
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Setup** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.11, C.4 P1/P12.

## Decision

`test_all.sh`: when no tests are marked `e2e`, skip the e2e step and print `e2e: skipped - no e2e tests yet`; treat pytest exit code 5 as success **only** for that step. Phase 12 installs Chromium and makes e2e mandatory — done, see D-95.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Related decisions:** [D-95](D-095-e2e-is-mandatory.md)
