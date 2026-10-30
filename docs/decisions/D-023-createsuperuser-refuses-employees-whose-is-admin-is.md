# D-23: createsuperuser refuses employees whose is_admin is off (in addition to unknown, not…

- **Status:** Accepted
- **Area:** Setup
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Setup** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.6, C.4 P1.

## Decision

`createsuperuser` refuses employees whose `is_admin` is off (in addition to unknown, not ACTIVE, or already having an account), so the superuser flags always match the directory (D-13). Set `is_admin` on the employee first. Tested by T-46/T-47.

## Consequences

- **Checked by:** [T-46](../testing.md#t-46)
- **Cited in code:** [`apps/directory/management/commands/createsuperuser.py`](../../apps/directory/management/commands/createsuperuser.py), [`apps/directory/services/accounts.py`](../../apps/directory/services/accounts.py), [`tests/directory/unit/test_accounts.py`](../../tests/directory/unit/test_accounts.py)
- **Related decisions:** [D-13](D-013-keep-user-is-staff-and-is-superuser.md)
