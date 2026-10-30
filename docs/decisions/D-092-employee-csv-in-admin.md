# D-92: Employee CSV in Admin

- **Status:** Accepted
- **Area:** Admin
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Admin** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-10, B.7.

## Decision

**Employee CSV in Admin** (own views; django-import-export would bypass `import_employees` and the audit log, and was removed in Phase 12, D-98). Import: upload (≤ 1 MB, UTF-8) → `import_employees(..., actor=admin, dry_run=True)` (same code, rolled back) → every error with its line, or a summary of created/updated (with changed fields)/unchanged/new teams → **Confirm** re-runs it for real on exactly that file (signed, valid 1 hour); all or nothing; audited with the admin as actor. Export (current list filters): the import columns plus `end_date`, formula-safe via payroll `safe_cell` (D-68) — the importer strips that leading `'` again, so an exported file re-imports with no changes; an EXPORT audit row records the row count.

## Consequences

- **Checked by:** [T-142](../testing.md#t-142), [T-143](../testing.md#t-143)
- **Cited in code:** [`apps/compensation/services/pay_import.py`](../../apps/compensation/services/pay_import.py), [`apps/directory/admin.py`](../../apps/directory/admin.py), [`apps/directory/forms.py`](../../apps/directory/forms.py), [`apps/directory/services/directory_admin.py`](../../apps/directory/services/directory_admin.py), [`apps/directory/services/importer.py`](../../apps/directory/services/importer.py)
- **Related decisions:** [D-68](D-068-export-csv-covers-all-current-records-of.md), [D-98](D-098-django-import-export-removed.md)
