# D-93: Admin access

- **Status:** Accepted
- **Area:** Admin
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Admin** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-10, B.8.

## Decision

**Admin access**: a custom default admin site admits only logged-in ACTIVE employees with is_admin; anyone else logged in gets 403 straight away, anonymous users go to `/login/` (refines D-29). Search and filters: employees by name, code, email, job title, team, department and manager name, filtered by status, team, department, is_admin, is_payroll and manager (managers only); teams by name/department; projects by code/name/active; timesheets by status, week, team and employee; AuditLog by action, entity type, actor, system actor and date (plus date hierarchy).

## Consequences

- **Checked by:** [T-144](../testing.md#t-144), [T-145](../testing.md#t-145)
- **Cited in code:** [`apps/audit/admin.py`](../../apps/audit/admin.py), [`apps/directory/admin_site.py`](../../apps/directory/admin_site.py), [`config/settings/base.py`](../../config/settings/base.py)
- **Related decisions:** [D-29](D-029-there-is-one-login-page-login-admin.md)
