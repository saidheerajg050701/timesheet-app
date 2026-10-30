# D-97: manage.py check --deploy HTTPS-only warnings do not apply

- **Status:** Accepted
- **Area:** Hardening
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Hardening** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.10, D.2.

## Decision

`manage.py check --deploy` **HTTPS-only warnings do not apply**: W004 (HSTS), W008 (SSL redirect), W012 (`SESSION_COOKIE_SECURE`), W016 (`CSRF_COOKIE_SECURE`). The app is served over plain HTTP on `127.0.0.1` (or a trusted office network, D.2): secure-only cookies would never be sent, so nobody could log in, and HSTS would force browsers onto HTTPS for the host. They are documented, not silenced, so they show up again if the app ever moves to a server — then set them. Every other deploy check passes once `.env` has `DJANGO_DEBUG=False` and a long random secret key.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
