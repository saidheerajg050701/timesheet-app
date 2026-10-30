# D-165: Only the filters that make a difference

- **Status:** Accepted
- **Area:** Reports
- **From:** Change 11b – Only the report filters that make a difference (commit `4dd8155`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Reports** area, recorded during Change 11b – Only the report filters that make a difference. It affects these parts of the specification: D-160, D-162.

## Decision

**Only the filters that make a difference** (Change 11b), decided in the report service: `scope_options` — the People choices (whole tree / direct reports / one manager's group) only when someone under the viewer manages people of their own (always for an admin with managers), otherwise none and the whole tree is used; `group_options` — **Team** when the report's people are in more than one team, **Manager** when By manager would have more than one row. The Group by control appears only when both apply; with one, that grouping is used and its table shown (kept in links as a hidden field); with none, no group table. The Excel's By team / By manager tabs follow the same list (`managing_tabs`), so the page and the file agree. An address asking for an option that isn't offered falls back to the default — no error and never anyone extra (for a manager offered no People choice, any `scope` / `manager` value means the whole tree). Someone who manages nobody still gets 403 for scope, group or manager parameters (D-160). Directors and admins keep every option.

## Consequences

- **Checked by:** [T-245](../testing.md#t-245), [T-254](../testing.md#t-254), [T-255](../testing.md#t-255), [T-256](../testing.md#t-256), [T-257](../testing.md#t-257)
- **Cited in code:** [`apps/reports/apps.py`](../../apps/reports/apps.py), [`apps/reports/services/cost_files.py`](../../apps/reports/services/cost_files.py), [`apps/reports/services/project_report/filters.py`](../../apps/reports/services/project_report/filters.py), [`apps/reports/services/project_report/scope.py`](../../apps/reports/services/project_report/scope.py), [`apps/reports/services/report_files.py`](../../apps/reports/services/report_files.py), [`apps/reports/templates/reports/project_budget.html`](../../apps/reports/templates/reports/project_budget.html), [`apps/reports/templates/reports/project_hours.html`](../../apps/reports/templates/reports/project_hours.html), [`tests/reports/integration/test_project_report.py`](../../tests/reports/integration/test_project_report.py)
- **Related decisions:** [D-160](D-160-reports-project-hours-who-sees-what.md)
