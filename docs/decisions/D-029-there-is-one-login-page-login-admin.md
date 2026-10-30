# D-29: There is one login page, /login/. /admin/login/ redirects there (keeping ?next=)

- **Status:** Accepted — later updated by D-93
- **Area:** Login
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Login** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.8, C.4 P3/P11.

## Decision

There is one login page, `/login/`. `/admin/login/` redirects there (keeping `?next=`); a logged-in employee without `is_admin` who opens `/admin/` gets 403.

## Consequences

- **Checked by:** [T-144](../testing.md#t-144)
- **Cited in code:** [`apps/directory/admin_site.py`](../../apps/directory/admin_site.py)
- **Updated later by:** [D-93](D-093-admin-access.md)
