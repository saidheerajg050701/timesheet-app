# D-170: Reports → Project budget: who sees what

- **Status:** Accepted
- **Area:** Costs
- **From:** Change 12 – Employee pay, project budgets and labour cost (commit `062a78f`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Costs** area, recorded during Change 12 – Employee pay, project budgets and labour cost. It affects these parts of the specification: B.3.

## Decision

**Reports → Project budget: who sees what** (`can_see_costs`, `can_see_everyones_costs`): managers and directors see **their own tree** — per-person hours, hourly rate used and cost, the Detail and their people's Rate missing — and project-wide budget totals; **payroll staff and admins see everyone** (payroll view only); anyone else gets **403** on the page and both downloads and has no menu item (Reports becomes a dropdown: Project hours, Project budget). Nobody here sees annual salaries, pay types' history or pay changes — those stay in Admin. People / Group by follow D-160 and D-165 (payroll counts as "everyone").

## Consequences

- **Checked by:** [T-266](../testing.md#t-266), [T-270](../testing.md#t-270)
- **Cited in code:** [`apps/analytics/views/__init__.py`](../../apps/analytics/views/__init__.py), [`apps/compensation/services/access.py`](../../apps/compensation/services/access.py), [`apps/directory/services/permissions.py`](../../apps/directory/services/permissions.py), [`apps/reports/apps.py`](../../apps/reports/apps.py), [`apps/reports/services/project_costs.py`](../../apps/reports/services/project_costs.py), [`apps/reports/services/project_report/queries.py`](../../apps/reports/services/project_report/queries.py), [`apps/reports/static/reports/budget.js`](../../apps/reports/static/reports/budget.js), [`apps/reports/urls.py`](../../apps/reports/urls.py), [`apps/reports/views.py`](../../apps/reports/views.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/directory/unit/test_permissions.py`](../../tests/directory/unit/test_permissions.py), [`tests/e2e/test_reports.py`](../../tests/e2e/test_reports.py), [`tests/reports/integration/test_project_costs.py`](../../tests/reports/integration/test_project_costs.py)
- **Related decisions:** [D-160](D-160-reports-project-hours-who-sees-what.md), [D-165](D-165-only-the-filters-that-make-a-difference.md)
