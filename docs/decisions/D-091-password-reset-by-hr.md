# D-91: Password reset by HR

- **Status:** Accepted
- **Area:** Admin
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Admin** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-2/FR-10, B.6.

## Decision

**Password reset by HR** from the employee's admin page: a temporary password typed twice that passes `AUTH_PASSWORD_VALIDATORS`; Argon2 hash stored and `User.must_change_password` set (migration `directory/0002`). The person's other sessions end (session hash), their axes lockout is cleared, and the UPDATE audit row holds only `{"changed": ["password"], "must_change_password": true, "lockout_cleared": n}`. While the flag is set every page except Profile, logout and static files redirects to Profile; the profile password change clears it. Not for yourself (use Profile) or people without an account. `/admin/password_change/` redirects to Profile so every change is audited. Passwords are never shown.

## Consequences

- **Checked by:** [T-141](../testing.md#t-141)
- **Cited in code:** [`apps/directory/admin.py`](../../apps/directory/admin.py), [`apps/directory/admin_site.py`](../../apps/directory/admin_site.py), [`apps/directory/middleware.py`](../../apps/directory/middleware.py), [`apps/directory/models.py`](../../apps/directory/models.py), [`apps/directory/services/accounts.py`](../../apps/directory/services/accounts.py), [`apps/directory/services/directory_admin.py`](../../apps/directory/services/directory_admin.py), [`config/settings/base.py`](../../config/settings/base.py)
