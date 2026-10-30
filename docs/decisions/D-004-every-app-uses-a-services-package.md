# D-04: Every app uses a services package

- **Status:** Accepted
- **Area:** Setup
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Setup** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.6, B.9, B.11, C.4.

## Decision

Every app uses a services package: `<app>/services/<module>.py` (e.g. `apps/payroll/services/publish.py`, `apps/analytics/services/metrics.py`).

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
