# D-162: By manager and By employee

- **Status:** Accepted
- **Area:** Reports
- **From:** Change 11 – Reports → Project hours (commit `23fcc6b`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Reports** area, recorded during Change 11 – Reports → Project hours. It affects these parts of the specification: B.4 FR-6.

## Decision

**By manager and By employee.** **By manager** (Group by = Manager): every manager in the report, depth-first by name and indented, with **Own group** = the manager + their direct reports who manage nobody — every person counted once, so the column adds up to the total — and **Including everyone below** (the roll-up: own group + the roll-ups of the managers under them); people whose manager isn't in the report and who manage nobody form "No manager in this report"; each manager links to their group (People = one manager's group, other filters kept). Loops in bad manager data never repeat anyone. **By team** (Group by = Team): directory team (department), "No team" last. **By employee**: everyone in scope employed during the period (`team.people_in_range`; inactive people only with counted hours, marked "(inactive)"), people with project hours first, then highlighted 0.00 rows, each with one note in this order: "Hours not approved yet" (their entries for the chosen projects are in weeks the Hours filter hides), "Worked on other projects", "Only non-project time", "On leave", "No time entered"; columns: code, name, team, manager, hours per task, project, Meetings, Training, Other, non-project, total, leave (context), note; names link to the read-only team member page. "Show people with no hours" (on by default) hides the 0.00 rows; the Summary still says "X with hours of Y people".

## Consequences

- **Checked by:** [T-246](../testing.md#t-246), [T-248](../testing.md#t-248), [T-253](../testing.md#t-253)
- **Cited in code:** [`apps/reports/apps.py`](../../apps/reports/apps.py), [`apps/reports/services/project_report/__init__.py`](../../apps/reports/services/project_report/__init__.py), [`apps/reports/services/project_report/aggregate.py`](../../apps/reports/services/project_report/aggregate.py), [`apps/reports/services/project_report/constants.py`](../../apps/reports/services/project_report/constants.py), [`apps/reports/services/project_report/queries.py`](../../apps/reports/services/project_report/queries.py), [`apps/reports/services/project_report/rows.py`](../../apps/reports/services/project_report/rows.py), [`apps/reports/static/reports/report.js`](../../apps/reports/static/reports/report.js), [`apps/reports/views.py`](../../apps/reports/views.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/e2e/test_reports.py`](../../tests/e2e/test_reports.py), [`tests/reports/integration/test_project_report.py`](../../tests/reports/integration/test_project_report.py)
