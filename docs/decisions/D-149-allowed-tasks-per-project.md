# D-149: Allowed tasks per project

- **Status:** Accepted
- **Area:** Data
- **From:** Change 10 – Project tasks and charge codes (commit `22466dc`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Data** area, recorded during Change 10 – Project tasks and charge codes. It affects these parts of the specification: B.4 FR-10.

## Decision

**Allowed tasks per project** (`Project.tasks`, many-to-many). Admin → Projects shows an "Allowed tasks" checkbox list; a new project starts with every active task ticked; the migration links every existing project to all 9 defaults. Changes go through `directory_admin.set_project_tasks`: one UPDATE "Project" audit row with the sorted task codes before/after (none when nothing changed; adding a project with tasks gives CREATE then this UPDATE). **Removing a task in use, or deactivating one, is allowed:** saved entries keep it (history is never rewritten), the admin sees "SEC is used by 2 saved entries of I-001; open weeks must choose another task when they are saved again.", and open weeks are fixed on their next save by the entry rule (D-151). Submitted or locked weeks can still be approved as they are: approval and payroll never re-check tasks (T-237). Only admins manage tasks and projects (D-87).

## Consequences

- **Checked by:** [T-228](../testing.md#t-228), [T-237](../testing.md#t-237)
- **Cited in code:** [`apps/projects/admin.py`](../../apps/projects/admin.py), [`apps/projects/apps.py`](../../apps/projects/apps.py), [`apps/projects/models.py`](../../apps/projects/models.py), [`apps/projects/services/project_admin.py`](../../apps/projects/services/project_admin.py), [`apps/projects/services/tasks.py`](../../apps/projects/services/tasks.py), [`apps/timesheets/migrations/0007_default_tasks.py`](../../apps/timesheets/migrations/0007_default_tasks.py), [`tests/factories.py`](../../tests/factories.py), [`tests/projects/integration/test_tasks.py`](../../tests/projects/integration/test_tasks.py)
- **Related decisions:** [D-87](D-087-d-26-ends-for-directory-data-only.md), [D-151](D-151-the-entry-rule-for-tasks.md)
