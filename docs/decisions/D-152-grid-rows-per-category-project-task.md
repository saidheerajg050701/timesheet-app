# D-152: Grid rows per (category, project, task)

- **Status:** Accepted
- **Area:** Grid
- **From:** Change 10 – Project tasks and charge codes (commit `22466dc`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Grid** area, recorded during Change 10 – Project tasks and charge codes. It affects these parts of the specification: B.4 FR-3, D-107, D-127, D-130.

## Decision

**Grid rows per (category, project, task).** Row keys `PROJECT:<project id>:<task code>` (history without a task `PROJECT:<id>`, others `MEETING:` …); cell and dialog ids include the task; project rows are ordered by project code, then task order. Each slot posts `entry-N-task` (the task code). **+ Add row:** Project work asks for the project, then a Task list with only that project's active allowed tasks (filled by `grid.js` from `task_choices`, sent once in the page); "Choose a task." until one is picked; an existing project + task row gets the Change 5 "already has a row" pointer; `timesheet_row` refuses anything `target_problem` refuses (400). **⋮ menu:** the item is now **Change row** (dialog "Change project, task or category"; the longer label made the menu shift on narrow screens) with the same Task list, pre-set to the row's task; changing the task moves every slot and merges into an existing project + task row as in D-130. The ⋮ button's accessible name includes the task ("Row actions for I-001 Customer Portal · DEV Development") so two task rows of one project can be told apart. The same in the employee grid, Edit directly and the Approvals edit.

## Consequences

- **Checked by:** [T-230](../testing.md#t-230), [T-231](../testing.md#t-231), [T-236](../testing.md#t-236)
- **Cited in code:** [`apps/projects/apps.py`](../../apps/projects/apps.py), [`apps/projects/models.py`](../../apps/projects/models.py), [`apps/projects/services/tasks.py`](../../apps/projects/services/tasks.py), [`apps/timesheets/forms.py`](../../apps/timesheets/forms.py), [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/static/timesheets/grid.js`](../../apps/timesheets/static/timesheets/grid.js), [`apps/timesheets/templates/timesheets/_grid.html`](../../apps/timesheets/templates/timesheets/_grid.html), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py), [`tests/e2e/helpers.py`](../../tests/e2e/helpers.py), [`tests/e2e/test_timesheets.py`](../../tests/e2e/test_timesheets.py), [`tests/projects/integration/test_tasks.py`](../../tests/projects/integration/test_tasks.py), [`tests/timesheets/integration/test_grid.py`](../../tests/timesheets/integration/test_grid.py), [`tests/timesheets/integration/test_row_actions.py`](../../tests/timesheets/integration/test_row_actions.py)
- **Related decisions:** [D-130](D-130-row-action-rules.md)
