# D-13: Keep User.is_staff and is_superuser in sync with Employee.is_admin, and User.is_active…

- **Status:** Accepted
- **Area:** Roles
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Roles** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.3, B.4 FR-1/FR-2, B.6, B.9, C.4 P1/P3.

## Decision

Keep `User.is_staff` and `is_superuser` in sync with `Employee.is_admin`, and `User.is_active` with `Employee.status`, whenever an Employee is saved.

## Consequences

- **Checked by:** [T-45](../testing.md#t-45), [T-48](../testing.md#t-48), [T-49](../testing.md#t-49), [T-54](../testing.md#t-54), [T-139](../testing.md#t-139)
- **Cited in code:** [`apps/directory/admin_site.py`](../../apps/directory/admin_site.py), [`apps/directory/backends.py`](../../apps/directory/backends.py), [`apps/directory/managers.py`](../../apps/directory/managers.py), [`apps/directory/models.py`](../../apps/directory/models.py), [`apps/directory/services/accounts.py`](../../apps/directory/services/accounts.py), [`apps/directory/services/directory_admin.py`](../../apps/directory/services/directory_admin.py), [`tests/conftest.py`](../../tests/conftest.py), [`tests/directory/integration/test_admin_edit.py`](../../tests/directory/integration/test_admin_edit.py), [`tests/directory/integration/test_auth_views.py`](../../tests/directory/integration/test_auth_views.py), [`tests/directory/integration/test_import_employees.py`](../../tests/directory/integration/test_import_employees.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py), [`tests/directory/unit/test_accounts.py`](../../tests/directory/unit/test_accounts.py)
