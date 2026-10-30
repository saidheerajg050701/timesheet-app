# D-151: The entry rule for tasks

- **Status:** Accepted
- **Area:** Rules
- **From:** Change 10 – Project tasks and charge codes (commit `22466dc`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Rules** area, recorded during Change 10 – Project tasks and charge codes. It affects these parts of the specification: B.4 FR-3, D-18.

## Decision

**The entry rule for tasks** (one place: `validate_entries` with `tasks.task_problem`). PROJECT entries need an active project (D-18) **and** a task that is active and allowed for that project: "project work needs a task — choose one for I-001.", "task SEC is no longer active.", "task SEC is not allowed for project I-001."; an unknown task code in the form → "unknown task."; every other category has no task: "only project work can have a task." (also a database CheckConstraint `task_only_for_project_work`). Messages name project entries by charge code ("09:00–12:00 I-001-DEV and 11:00–13:00 Meetings overlap.") so they land on the right cell. **History** is never rewritten: entries saved before tasks keep an empty task; saving such a week again (Save draft, Submit, Edit directly, the Approvals edit) needs a task on its project rows — ⋮ Change row sets it for a whole row. All other rules are unchanged. Audit snapshots of entries include the task code.

## Consequences

- **Checked by:** [T-229](../testing.md#t-229), [T-232](../testing.md#t-232), [T-237](../testing.md#t-237)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/projects/apps.py`](../../apps/projects/apps.py), [`apps/projects/models.py`](../../apps/projects/models.py), [`apps/projects/services/tasks.py`](../../apps/projects/services/tasks.py), [`apps/timesheets/migrations/0007_default_tasks.py`](../../apps/timesheets/migrations/0007_default_tasks.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/grid_rows.py`](../../apps/timesheets/services/grid_rows.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/factories.py`](../../tests/factories.py), [`tests/forms.py`](../../tests/forms.py), [`tests/projects/integration/test_tasks.py`](../../tests/projects/integration/test_tasks.py), [`tests/timesheets/integration/test_change_requests.py`](../../tests/timesheets/integration/test_change_requests.py), [`tests/timesheets/unit/test_validation.py`](../../tests/timesheets/unit/test_validation.py)
- **Related decisions:** [D-18](D-018-project-entries-must-have-an-active-project.md)
