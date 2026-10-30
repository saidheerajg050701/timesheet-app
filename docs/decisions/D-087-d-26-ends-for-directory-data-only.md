# D-87: D-26 ends for directory data only

- **Status:** Accepted
- **Area:** Admin
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Admin** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-10.

## Decision

**D-26 ends for directory data only.** Editable in Admin: **Employee** (first/last name, job title, location, email, team, manager, hire date, expected weekly hours typed as hours and stored as minutes, is_admin, is_payroll; new employees can be added), **Team** (name, department; add), **Project** (name, active; code only when adding). Not in the employee form: `employee_code` after creation, `status` and `end_date` (Deactivate/Reactivate only). Read-only: Timesheet, TimeEntry, PeriodApproval, ChangeRequest, AuditLog, PayrollWeek, User (masked password) and the django-axes records; Django's `Group` is unregistered (access comes from is_admin, D-13). **Nothing can be deleted in Admin** (no delete permission, no "delete selected"); retire a project by clearing Active, an employee by deactivating. A changed expected weekly hours value applies to every week computed afterwards (no per-week history).

## Consequences

- **Checked by:** [T-134](../testing.md#t-134), [T-135](../testing.md#t-135), [T-136](../testing.md#t-136)
- **Cited in code:** [`apps/audit/admin.py`](../../apps/audit/admin.py), [`apps/directory/admin.py`](../../apps/directory/admin.py), [`apps/directory/admin_base.py`](../../apps/directory/admin_base.py), [`apps/directory/admin_site.py`](../../apps/directory/admin_site.py), [`apps/directory/services/directory_admin.py`](../../apps/directory/services/directory_admin.py), [`apps/projects/services/projects.py`](../../apps/projects/services/projects.py), [`tests/directory/integration/test_admin.py`](../../tests/directory/integration/test_admin.py)
- **Related decisions:** [D-13](D-013-keep-user-is-staff-and-is-superuser.md), [D-26](D-026-until-phase-11-django-admin-is-view.md)
