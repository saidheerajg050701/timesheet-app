# D-103: Charts use the tokens

- **Status:** Accepted
- **Area:** UI
- **From:** Change 1 – Modern UI (commit `7f19f32`)
- **Recorded:** 2026-10-24

## Context

A decision in the **UI** area, recorded during Change 1 – Modern UI. It affects these parts of the specification: B.4 FR-5/FR-6.

## Decision

**Charts use the tokens**: `dashboard.js` and `team.js` read `--ts-chart-series` (the accent `#2563eb`, which passes the palette validator against the light surface), `--ts-chart-muted` and `--ts-chart-grid` with `getComputedStyle`, falling back to the same values. Every chart keeps its table or text version (D-80).

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/analytics/static/analytics/dashboard.js`](../../apps/analytics/static/analytics/dashboard.js), [`apps/analytics/static/analytics/team.js`](../../apps/analytics/static/analytics/team.js), [`apps/reports/static/reports/budget.js`](../../apps/reports/static/reports/budget.js), [`apps/reports/static/reports/report.js`](../../apps/reports/static/reports/report.js), [`static/css/theme.css`](../../static/css/theme.css)
- **Related decisions:** [D-80](D-080-charts-use-the-vendored-chart-js-with.md)
