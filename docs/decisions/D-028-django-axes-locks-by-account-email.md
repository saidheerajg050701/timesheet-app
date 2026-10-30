# D-28: django-axes locks by account (email)

- **Status:** Accepted
- **Area:** Login
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Login** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-1, C.4 P3, D.1.

## Decision

django-axes locks by **account (email)**: 5 failed attempts lock that email for 15 minutes from any computer; `uv run python manage.py axes_reset` clears it (it clears all lockouts; `axes_reset_username <email>` clears just one). The email is trimmed and lower-cased before counting, the 5th failure already shows the locked page, and `axes.W006` (which recommends adding the IP address) is silenced for this reason.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/directory/services/login.py`](../../apps/directory/services/login.py), [`config/settings/base.py`](../../config/settings/base.py), [`tests/directory/integration/test_auth_views.py`](../../tests/directory/integration/test_auth_views.py)
