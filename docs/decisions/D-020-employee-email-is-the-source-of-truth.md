# D-20: Employee.email is the source of truth

- **Status:** Accepted
- **Area:** Data
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Data** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.4 FR-2, B.6, B.9.

## Decision

`Employee.email` is the source of truth. `User.email` updates automatically (lower-cased) when HR changes `Employee.email`; both stay unique.

## Consequences

- **Checked by:** [T-45](../testing.md#t-45), [T-50](../testing.md#t-50), [T-51](../testing.md#t-51), [T-54](../testing.md#t-54), [T-139](../testing.md#t-139)
- **Cited in code:** [`apps/directory/managers.py`](../../apps/directory/managers.py), [`apps/directory/models.py`](../../apps/directory/models.py), [`apps/directory/services/accounts.py`](../../apps/directory/services/accounts.py), [`tests/directory/integration/test_admin_edit.py`](../../tests/directory/integration/test_admin_edit.py), [`tests/directory/integration/test_import_employees.py`](../../tests/directory/integration/test_import_employees.py), [`tests/directory/unit/test_accounts.py`](../../tests/directory/unit/test_accounts.py)
