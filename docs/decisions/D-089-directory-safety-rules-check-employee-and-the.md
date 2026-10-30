# D-89: Directory safety rules (check_employee, and the same checks in the CSV import)

- **Status:** Accepted
- **Area:** Admin
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Admin** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-10, B.9.

## Decision

Directory safety rules (`check_employee`, and the same checks in the CSV import): nobody is their own manager; a manager change that makes a reporting loop is refused; a newly assigned manager must be ACTIVE; you cannot remove your own admin flag; at least one ACTIVE admin always remains; a new or changed email is lower-cased, unique across Employee and User (any case) and must end in `COMPANY_EMAIL_DOMAIN`; a changed hire date may not be after the person's first saved entry or after their end date. The command-line import and `seed_demo` keep the Phase 2 rules plus the loop and last-admin checks; the domain and "your own" rules apply when an admin imports.

## Consequences

- **Checked by:** [T-139](../testing.md#t-139), [T-140](../testing.md#t-140), [T-142](../testing.md#t-142)
- **Cited in code:** [`apps/directory/services/directory_admin.py`](../../apps/directory/services/directory_admin.py), [`apps/directory/services/importer.py`](../../apps/directory/services/importer.py), [`apps/directory/services/rules.py`](../../apps/directory/services/rules.py), [`tests/directory/integration/test_admin_edit.py`](../../tests/directory/integration/test_admin_edit.py), [`tests/directory/unit/test_directory_rules.py`](../../tests/directory/unit/test_directory_rules.py)
