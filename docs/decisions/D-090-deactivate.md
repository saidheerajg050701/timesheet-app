# D-90: Deactivate

- **Status:** Accepted
- **Area:** Admin
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Admin** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-10, D-19.

## Decision

**Deactivate** (admin action with a confirmation page; all or nothing for the selection): status INACTIVE and `end_date` (default today; allowed from the hire date and the last saved entry up to today, never in the future). The User becomes inactive (D-13), so an open session ends on the next request; history stays and existing timesheets can still be approved and paid (D-19). Refused for yourself, for someone who still manages ACTIVE people outside the selection ("reassign their reports first"), and when no ACTIVE admin would remain. **Reactivate**: ACTIVE with `end_date` cleared, hire date unchanged. Both write an UPDATE audit row.

## Consequences

- **Checked by:** [T-137](../testing.md#t-137), [T-138](../testing.md#t-138)
- **Cited in code:** [`apps/directory/admin.py`](../../apps/directory/admin.py), [`apps/directory/services/directory_admin.py`](../../apps/directory/services/directory_admin.py), [`apps/directory/services/importer.py`](../../apps/directory/services/importer.py), [`apps/directory/services/rules.py`](../../apps/directory/services/rules.py), [`tests/directory/integration/test_admin_edit.py`](../../tests/directory/integration/test_admin_edit.py)
- **Related decisions:** [D-13](D-013-keep-user-is-staff-and-is-superuser.md), [D-19](D-019-add-employee-end-date-nullable-set-on.md)
