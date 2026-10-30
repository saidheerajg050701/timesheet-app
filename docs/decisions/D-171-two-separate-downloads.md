# D-171: Two separate downloads

- **Status:** Accepted
- **Area:** Costs
- **From:** Change 12 – Employee pay, project budgets and labour cost (commit `062a78f`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Costs** area, recorded during Change 12 – Employee pay, project budgets and labour cost. It affects these parts of the specification: D-68, D-163.

## Decision

**Two separate downloads.** Costs: `project-costs_<from>_to_<to>.xlsx` with Summary (filters, generated at/by, the notes), By project, By team / By manager (as offered, D-165), By task, By pay type, By pay period, By employee, Detail (one row per entry with hourly rate and cost) and Rate missing (when there is any); money as exact numbers formatted "$"#,##0.00; and `….csv` = the Detail (date, week_start, employee_code, employee_name, team, manager, project_code, project_name, task_code, task_name, charge_code, hours, pay_type, hourly_rate, cost, rate_missing) — no salaries, no reasons; formula-safe text; one EXPORT "ProjectCosts" audit row per download (viewer, filters, rows). Hours: links to the Change 11 report files with these filters and Approved (`project-hours_…`); payroll staff who manage nobody get no hours link, because that report shows them only their own hours (D-160). Speed (`seed_demo --large`, HR): last pay period page 0.6 s, files 0.5 s; 12 weeks page 1.1 s, CSV 1.3 s, Excel 5 s; a whole year page 3.8 s, CSV 5.3 s, Excel ~25 s (millions of cells — use the CSV for that much).

## Consequences

- **Checked by:** [T-265](../testing.md#t-265), [T-267](../testing.md#t-267), [T-270](../testing.md#t-270)
- **Cited in code:** [`apps/reports/apps.py`](../../apps/reports/apps.py), [`apps/reports/services/cost_files.py`](../../apps/reports/services/cost_files.py), [`apps/reports/services/project_costs.py`](../../apps/reports/services/project_costs.py), [`apps/reports/services/report_files.py`](../../apps/reports/services/report_files.py), [`apps/reports/views.py`](../../apps/reports/views.py), [`apps/timesheets/templatetags/timesheet_tags.py`](../../apps/timesheets/templatetags/timesheet_tags.py), [`tests/e2e/test_reports.py`](../../tests/e2e/test_reports.py), [`tests/reports/integration/test_project_costs.py`](../../tests/reports/integration/test_project_costs.py)
- **Related decisions:** [D-160](D-160-reports-project-hours-who-sees-what.md), [D-165](D-165-only-the-filters-that-make-a-difference.md)
