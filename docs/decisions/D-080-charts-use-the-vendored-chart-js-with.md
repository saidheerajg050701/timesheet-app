# D-80: Charts use the vendored Chart.js with data only through json_script

- **Status:** Accepted
- **Area:** Analytics
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Analytics** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-5, B.10.

## Decision

Charts use the vendored Chart.js with data only through `json_script`; every chart has a table or text with the same numbers; friendly empty states. Viewing never writes (D-34) and uses a fixed number of queries whatever the range.

## Consequences

- **Checked by:** [T-120](../testing.md#t-120), [T-121](../testing.md#t-121)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/analytics/static/analytics/dashboard.js`](../../apps/analytics/static/analytics/dashboard.js), [`apps/analytics/static/analytics/team.js`](../../apps/analytics/static/analytics/team.js), [`apps/analytics/views/dashboard.py`](../../apps/analytics/views/dashboard.py)
- **Related decisions:** [D-34](D-034-locked-and-missed-are-worked-out-when.md)
