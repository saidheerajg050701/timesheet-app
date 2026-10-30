# D-163: Downloads

- **Status:** Accepted
- **Area:** Reports
- **From:** Change 11 – Reports → Project hours (commit `23fcc6b`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Reports** area, recorded during Change 11 – Reports → Project hours. It affects these parts of the specification: B.10, D-68.

## Decision

**Downloads.** **Excel** (`openpyxl`, the one new package): managers/directors/admins get Summary (filters, generated at and by), By project, By team, By manager, By employee, By task, Project × task, Detail; an employee's own report Summary, By project, By task, Project × task, By week, Detail. Bold frozen header rows, sized columns, hours as numbers formatted 0.00, written row by row (write-only). **CSV** = the Detail: one row per counted entry (non-project entries with their category and no project or task) — date, week_start, employee_code, employee_name, team, department, manager, project_code, project_name, task_code, task_name, charge_code, category, hours, week_status — **never the reason**; UTF-8 with BOM like the payroll CSVs. Text cells are formula-safe (`safe_cell`, D-68). File names `project-hours_<from>_to_<to>.xlsx/.csv`, with the employee code for one's own report (`project-hours_DEV2_2026-09-27_to_2026-10-10.xlsx`). Every download writes one **EXPORT** audit row: entity "ProjectReport", id "<from>..<to>", the viewer, the format, the filters and the row count — never the data.

## Consequences

- **Checked by:** [T-249](../testing.md#t-249), [T-250](../testing.md#t-250)
- **Cited in code:** [`apps/reports/apps.py`](../../apps/reports/apps.py), [`apps/reports/services/project_report/__init__.py`](../../apps/reports/services/project_report/__init__.py), [`apps/reports/services/project_report/queries.py`](../../apps/reports/services/project_report/queries.py), [`apps/reports/services/project_report/rows.py`](../../apps/reports/services/project_report/rows.py), [`apps/reports/services/report_files.py`](../../apps/reports/services/report_files.py), [`apps/reports/static/reports/report.js`](../../apps/reports/static/reports/report.js), [`apps/reports/views.py`](../../apps/reports/views.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/reports/integration/test_project_report.py`](../../tests/reports/integration/test_project_report.py)
- **Related decisions:** [D-68](D-068-export-csv-covers-all-current-records-of.md)
