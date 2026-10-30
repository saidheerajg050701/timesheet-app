# D-150: Charge code

- **Status:** Accepted
- **Area:** Data
- **From:** Change 10 – Project tasks and charge codes (commit `22466dc`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Data** area, recorded during Change 10 – Project tasks and charge codes. It affects these parts of the specification: B.4 FR-3.

## Decision

**Charge code** = "<project code>-<task code>", e.g. **I-001-DEV** (`tasks.charge_code`). Worked out, **never stored**. Project work without a task (saved before Change 10) has the project code alone and the label "Task not recorded" (`TASK_NOT_RECORDED`). Shown on every grid row as a small chip next to "I-001 Customer Portal · DEV Development" — the employee's week (editable and read-only), Edit directly, the Approvals period page and edit, change requests and the Team week view all use the same grid — in validation messages and in the analytics tables.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/projects/apps.py`](../../apps/projects/apps.py), [`apps/projects/models.py`](../../apps/projects/models.py), [`apps/projects/services/tasks.py`](../../apps/projects/services/tasks.py), [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/projects/integration/test_tasks.py`](../../tests/projects/integration/test_tasks.py)
