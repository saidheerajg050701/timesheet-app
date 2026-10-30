# D-172: Demo pay and budgets

- **Status:** Accepted
- **Area:** Data
- **From:** Change 12 – Employee pay, project budgets and labour cost (commit `062a78f`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Data** area, recorded during Change 12 – Employee pay, project budgets and labour cost. It affects these parts of the specification: B.7.

## Decision

**Demo pay and budgets** (`seed_demo`): everyone gets pay from the later of the history start and their hire date — salaried by job title (e.g. Software Engineer ~$125,000, rate = salary ÷ 2,080), hourly for Operations Analysts, Support Specialists and Executive Assistants ($24–$33.50) — DEV1 a 6 % raise four periods before the end, and the first Data staff member none (Rate missing). Budgets on I-001 … I-007 come from each project's approved cost so far, so the demo shows On track, At risk (I-003, ~90 %) and Over budget (I-002, ~115 %); I-008 (closed) has none. Pay rows are audited like any pay change; budgets are part of the projects' CREATE audit rows.

## Consequences

- **Checked by:** [T-268](../testing.md#t-268)
- **Cited in code:** [`apps/directory/services/demo/constants.py`](../../apps/directory/services/demo/constants.py), [`apps/directory/services/demo/pay.py`](../../apps/directory/services/demo/pay.py), [`tests/reports/integration/test_project_costs.py`](../../tests/reports/integration/test_project_costs.py)
