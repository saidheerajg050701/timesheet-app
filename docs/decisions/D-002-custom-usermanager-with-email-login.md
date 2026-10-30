# D-02: Custom UserManager with email login

- **Status:** Accepted
- **Area:** Setup
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Setup** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.6, C.4 P1.

## Decision

Custom `UserManager` with email login. `create_user` / `create_superuser` require an employee. `createsuperuser` asks for an `employee_code` that must exist, be ACTIVE and have no account. Normal accounts come from `seed_demo` or sign-up.

## Consequences

- **Checked by:** [T-44](../testing.md#t-44), [T-45](../testing.md#t-45), [T-46](../testing.md#t-46), [T-47](../testing.md#t-47)
- **Cited in code:** [`apps/directory/management/commands/createsuperuser.py`](../../apps/directory/management/commands/createsuperuser.py), [`apps/directory/managers.py`](../../apps/directory/managers.py), [`apps/directory/models.py`](../../apps/directory/models.py), [`apps/directory/services/accounts.py`](../../apps/directory/services/accounts.py), [`config/settings/base.py`](../../config/settings/base.py), [`tests/directory/unit/test_accounts.py`](../../tests/directory/unit/test_accounts.py)
