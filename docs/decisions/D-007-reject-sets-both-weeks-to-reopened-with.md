# D-07: Reject sets both weeks to REOPENED with reopen_until set per D-21.

- **Status:** Accepted
- **Area:** Timesheet status
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Timesheet status** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.4 FR-7, B.5, B.11 T-31.

## Decision

Reject sets both weeks to REOPENED with `reopen_until` set per D-21.

## Consequences

- **Checked by:** [T-93](../testing.md#t-93), [T-189](../testing.md#t-189)
- **Cited in code:** [`apps/directory/services/demo/approvals.py`](../../apps/directory/services/demo/approvals.py), [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py)
- **Related decisions:** [D-21](D-021-reopen-window.md)
