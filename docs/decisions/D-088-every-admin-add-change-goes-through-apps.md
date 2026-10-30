# D-88: Every Admin add/change goes through apps/directory/services/directory_admin.py…

- **Status:** Accepted
- **Area:** Admin
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Admin** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.10, CLAUDE.md.

## Decision

Every Admin add/change goes through `apps/directory/services/directory_admin.py` (`save_employee`, `save_team`; `save_project` / `save_task` are in `apps/projects/services/project_admin.py` since R2, D-174; actions call `deactivate`, `reactivate`, `reset_password`, `export_employees`), which checks the rules, saves and writes the CREATE/UPDATE audit row with the admin as actor in one transaction; before/after hold only the changed fields and a save with no changes writes nothing. Audit `entity_id` as before: employee code, team name (before a rename), project code.

## Consequences

- **Checked by:** [T-133](../testing.md#t-133), [T-134](../testing.md#t-134), [T-239](../testing.md#t-239)
- **Cited in code:** [`apps/directory/admin_base.py`](../../apps/directory/admin_base.py), [`apps/directory/services/directory_admin.py`](../../apps/directory/services/directory_admin.py), [`apps/projects/admin.py`](../../apps/projects/admin.py), [`apps/projects/services/project_admin.py`](../../apps/projects/services/project_admin.py), [`tests/directory/integration/test_admin_edit.py`](../../tests/directory/integration/test_admin_edit.py)
- **Related decisions:** [D-174](D-174-refactor-r2-own-apps-everything-in-apps.md)
