# D-168: Project budgets

- **Status:** Accepted
- **Area:** Data
- **From:** Change 12 – Employee pay, project budgets and labour cost (commit `062a78f`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Data** area, recorded during Change 12 – Employee pay, project budgets and labour cost. It affects these parts of the specification: B.6, D-88.

## Decision

**Project budgets.** `Project.budget` (USD, ≥ 0, optional; empty = "No budget set") and `Project.costs_from` (optional; empty = all time), edited on the Admin project page through the audited `save_project`; audit rows keep amounts and dates as exact text.

## Consequences

- **Checked by:** [T-261](../testing.md#t-261), [T-270](../testing.md#t-270)
- **Cited in code:** [`apps/directory/services/directory_admin.py`](../../apps/directory/services/directory_admin.py), [`apps/projects/admin.py`](../../apps/projects/admin.py), [`apps/projects/apps.py`](../../apps/projects/apps.py), [`apps/projects/models.py`](../../apps/projects/models.py), [`apps/projects/services/project_admin.py`](../../apps/projects/services/project_admin.py), [`apps/reports/apps.py`](../../apps/reports/apps.py), [`tests/compensation/integration/test_pay.py`](../../tests/compensation/integration/test_pay.py), [`tests/e2e/test_reports.py`](../../tests/e2e/test_reports.py)
