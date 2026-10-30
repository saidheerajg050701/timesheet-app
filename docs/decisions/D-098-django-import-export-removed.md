# D-98: django-import-export removed

- **Status:** Accepted
- **Area:** Setup
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Setup** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.2, C.2, D-92.

## Decision

**django-import-export removed** (`uv remove django-import-export`, also dropping `tablib` and `diff-match-patch`); nothing used it — the admin CSV import/export are our own audited views (D-92). Removed from CLAUDE.md, B.2 and the Phase 1 prompt.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Related decisions:** [D-92](D-092-employee-csv-in-admin.md)
