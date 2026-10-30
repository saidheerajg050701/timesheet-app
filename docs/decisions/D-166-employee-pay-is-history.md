# D-166: Change 12 – Employee pay is history

- **Status:** Accepted
- **Area:** Pay
- **From:** Change 12 – Employee pay, project budgets and labour cost (commit `062a78f`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Pay** area, recorded during Change 12 – Employee pay, project budgets and labour cost. It affects these parts of the specification: B.6.

## Decision

**Change 12 – Employee pay is history.** `PayRecord` (directory app): SALARIED (annual salary + the hourly rate HR fixes; suggested = salary ÷ 2,080, 40 h × 52 weeks, half-up to cents, used when the rate is left empty) or HOURLY (hourly rate), each with `effective_from`. A pay change — or a correction for the same date — is a **new record**: saving an existing record, deleting, and bulk updates/deletes raise `PayHistoryError`. The record in force on a day is the one with the latest `effective_from` up to that day, the newest for a tie (`pay.record_on`). Back-dated changes are allowed (not before the hire date) and re-price work from that date — older dates keep their rate. Money is `Decimal` with exact cents everywhere, never float. Every change writes a CREATE "Pay" audit row (before = the pay in force until then, after, `correction`).

## Consequences

- **Checked by:** [T-258](../testing.md#t-258), [T-270](../testing.md#t-270)
- **Cited in code:** [`apps/compensation/admin.py`](../../apps/compensation/admin.py), [`apps/compensation/apps.py`](../../apps/compensation/apps.py), [`apps/compensation/models.py`](../../apps/compensation/models.py), [`apps/compensation/services/pay.py`](../../apps/compensation/services/pay.py), [`apps/compensation/services/pay_import.py`](../../apps/compensation/services/pay_import.py), [`apps/compensation/templates/admin/compensation/pay.html`](../../apps/compensation/templates/admin/compensation/pay.html), [`apps/reports/apps.py`](../../apps/reports/apps.py), [`tests/compensation/integration/test_pay.py`](../../tests/compensation/integration/test_pay.py), [`tests/e2e/test_reports.py`](../../tests/e2e/test_reports.py)
