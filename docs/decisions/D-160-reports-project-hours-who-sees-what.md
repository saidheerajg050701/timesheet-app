# D-160: Change 11 – Reports → Project hours: who sees what

- **Status:** Accepted
- **Area:** Reports
- **From:** Change 11 – Reports → Project hours (commit `23fcc6b`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Reports** area, recorded during Change 11 – Reports → Project hours. It affects these parts of the specification: B.3, D-31, D-81.

## Decision

**Change 11 – Reports → Project hours: who sees what.** Everyone has **Reports** in the menu. The people in a report come from one function, `project_report.report_people`, using the Team rules (`manager_map`, `reporting_tree_ids`): someone who manages nobody — an employee, a payroll-only user — sees **only their own hours** (and any `scope`, `group` or `manager` in the address is **403**); a manager sees **themselves plus their whole tree**; a director is simply a manager whose tree contains managers, so they see all their managers' groups; an **admin** sees everyone. Managers choose **People** = whole tree (default; "Everyone" for an admin) / direct reports only (themselves + direct reports) / **one manager's group** (that manager + their whole tree; the viewer, someone in their tree, or anyone for an admin — otherwise, or for an unknown code, **403**). The same check runs for the page, every filter value and both downloads. Teams and managers are as they are today (moves are not tracked).

## Consequences

- **Checked by:** [T-244](../testing.md#t-244), [T-245](../testing.md#t-245), [T-252](../testing.md#t-252), [T-253](../testing.md#t-253)
- **Cited in code:** [`apps/analytics/views/__init__.py`](../../apps/analytics/views/__init__.py), [`apps/directory/services/permissions.py`](../../apps/directory/services/permissions.py), [`apps/reports/apps.py`](../../apps/reports/apps.py), [`apps/reports/services/project_report/__init__.py`](../../apps/reports/services/project_report/__init__.py), [`apps/reports/services/project_report/constants.py`](../../apps/reports/services/project_report/constants.py), [`apps/reports/services/project_report/queries.py`](../../apps/reports/services/project_report/queries.py), [`apps/reports/services/project_report/rows.py`](../../apps/reports/services/project_report/rows.py), [`apps/reports/services/project_report/scope.py`](../../apps/reports/services/project_report/scope.py), [`apps/reports/static/reports/report.js`](../../apps/reports/static/reports/report.js), [`apps/reports/urls.py`](../../apps/reports/urls.py), [`apps/reports/views.py`](../../apps/reports/views.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/directory/unit/test_permissions.py`](../../tests/directory/unit/test_permissions.py), [`tests/e2e/test_reports.py`](../../tests/e2e/test_reports.py), [`tests/reports/integration/test_project_report.py`](../../tests/reports/integration/test_project_report.py)
