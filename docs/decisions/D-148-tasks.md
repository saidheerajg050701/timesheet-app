# D-148: Change 10 – Tasks

- **Status:** Accepted
- **Area:** Data
- **From:** Change 10 – Project tasks and charge codes (commit `22466dc`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Data** area, recorded during Change 10 – Project tasks and charge codes. It affects these parts of the specification: B.6.

## Decision

**Change 10 – Tasks.** `Task` (code ≤ 10 characters, unique; name; description; active; sort order) says what project work was spent on. Admins add and edit tasks in Admin → Tasks (`directory_admin.save_task`, CREATE / UPDATE audit rows, D-88); the code is read-only once added (entries and audit rows refer to it); tasks are **never deleted** (no delete permission; `TimeEntry.task` is PROTECT) — clear Active instead. The change page shows how many saved entries use the task. **Defaults:** PLN Planning & Analysis, DES Design & Architecture, DEV Development, TST Testing & QA, REL Release & DevOps, SUP Support & Bug Fixes, SEC Security & Compliance, DOC Documentation & Knowledge Transfer, MTG Project Meetings & Coordination (sort 10…90, with the agreed descriptions), created by the data migration `timesheets/0007_default_tasks` (get-or-create, safe to repeat; reversing it deletes nothing) and so present in every database, `seed_demo` included.

## Consequences

- **Checked by:** [T-227](../testing.md#t-227), [T-228](../testing.md#t-228)
- **Cited in code:** [`apps/directory/services/demo/projects.py`](../../apps/directory/services/demo/projects.py), [`apps/projects/admin.py`](../../apps/projects/admin.py), [`apps/projects/apps.py`](../../apps/projects/apps.py), [`apps/projects/models.py`](../../apps/projects/models.py), [`apps/projects/services/project_admin.py`](../../apps/projects/services/project_admin.py), [`apps/projects/services/tasks.py`](../../apps/projects/services/tasks.py), [`apps/timesheets/migrations/0007_default_tasks.py`](../../apps/timesheets/migrations/0007_default_tasks.py), [`tests/projects/integration/test_tasks.py`](../../tests/projects/integration/test_tasks.py)
- **Related decisions:** [D-88](D-088-every-admin-add-change-goes-through-apps.md)
