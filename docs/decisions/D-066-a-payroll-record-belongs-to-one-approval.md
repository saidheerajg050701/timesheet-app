# D-66: A payroll record belongs to one approval decision (approved_at =…

- **Status:** Accepted
- **Area:** Payroll
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Payroll** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.6, B.9 #13.

## Decision

A payroll record belongs to one approval decision (`approved_at` = `PeriodApproval.decided_at`): publishing the same decision again is a no-op; a live record from an older decision is superseded and the next version written. Partial unique constraint `one_live_record_per_week` (at most one non-SUPERSEDED record per employee and week). *Extended by D-118: a SETTLED version is the live record of its week.*

## Consequences

- **Checked by:** [T-106](../testing.md#t-106), [T-109](../testing.md#t-109)
- **Cited in code:** [`apps/payroll/models.py`](../../apps/payroll/models.py), [`apps/payroll/services/publish.py`](../../apps/payroll/services/publish.py), [`tests/payroll/integration/test_payroll_publish.py`](../../tests/payroll/integration/test_payroll_publish.py)
- **Related decisions:** [D-118](D-118-settled-weeks.md)
