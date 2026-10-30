# D-67: Append-only (D-15) enforced in code

- **Status:** Accepted
- **Area:** Payroll
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Payroll** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.6, B.10.

## Decision

Append-only (D-15) enforced in code: `PayrollWeek.save()` refuses changes to frozen fields and any move other than CURRENT→EXPORTED→PAID or →SUPERSEDED, each lifecycle field set once by its own move; `delete()`, `QuerySet.update()`, `bulk_update()` and `QuerySet.delete()` raise AppendOnlyError; the admin is view-only.

## Consequences

- **Checked by:** [T-104](../testing.md#t-104)
- **Cited in code:** [`apps/payroll/admin.py`](../../apps/payroll/admin.py), [`apps/payroll/models.py`](../../apps/payroll/models.py)
- **Related decisions:** [D-15](D-015-append-only-means-snapshot-and-hours-fields.md)
