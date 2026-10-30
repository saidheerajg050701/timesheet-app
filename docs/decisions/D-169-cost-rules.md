# D-169: Cost rules

- **Status:** Accepted
- **Area:** Costs
- **From:** Change 12 – Employee pay, project budgets and labour cost (commit `062a78f`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Costs** area, recorded during Change 12 – Employee pay, project budgets and labour cost. It affects these parts of the specification: D-161.

## Decision

**Cost rules** (one place: `apps/reports/services/project_costs.py`, built on the Project hours report so the hours always match it). **Approved hours only** — the page has no Hours filter; any `hours` parameter is ignored. Cost of a Project-work entry = hours × the hourly rate in force on its work date, rounded half-up to cents (`pay.labour_cost`); every total is the sum of the rounded rows, so the page, Excel and CSV add up. Break, leave, Meetings, Training and Other are never charged to projects. Overtime uses the same rate ("overtime premium not included"). An entry with no pay on its date is **not costed** (never $0): it is listed under **Rate missing** (person, hours, dates), warned about on the page and noted per project. Per project: **total cost to date** = the whole project's approved cost since `costs_from` — everyone's, whatever the period or the viewer's tree; **remaining** = budget − total; **% used** = total ÷ budget (one decimal); **status** On track (< `BUDGET_AT_RISK_PERCENT`, default 80), At risk (up to `BUDGET_OVER_PERCENT`, default 100), Over budget (above it), No budget set; a 0 budget is Over budget as soon as anything is spent. Cost and hours **this period** are the report's people's. Projects listed: the chosen ones; otherwise those the report's people worked on, plus every budgeted project for admins and payroll. Breakdowns: team or manager (D-162, D-165), task, pay type (in force on the date), pay period, By employee (pay type and hourly rate(s) used, hours, cost).

## Consequences

- **Checked by:** [T-262](../testing.md#t-262), [T-263](../testing.md#t-263), [T-264](../testing.md#t-264), [T-265](../testing.md#t-265), [T-269](../testing.md#t-269), [T-270](../testing.md#t-270)
- **Cited in code:** [`apps/compensation/services/pay.py`](../../apps/compensation/services/pay.py), [`apps/reports/apps.py`](../../apps/reports/apps.py), [`apps/reports/services/project_costs.py`](../../apps/reports/services/project_costs.py), [`apps/reports/services/project_report/rows.py`](../../apps/reports/services/project_report/rows.py), [`apps/reports/views.py`](../../apps/reports/views.py), [`apps/timesheets/templatetags/timesheet_tags.py`](../../apps/timesheets/templatetags/timesheet_tags.py), [`config/settings/base.py`](../../config/settings/base.py), [`tests/e2e/test_reports.py`](../../tests/e2e/test_reports.py), [`tests/reports/integration/test_project_costs.py`](../../tests/reports/integration/test_project_costs.py)
- **Related decisions:** [D-162](D-162-by-manager-and-by-employee.md), [D-165](D-165-only-the-filters-that-make-a-difference.md)
