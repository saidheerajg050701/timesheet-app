# D-167: Only admins see or change pay

- **Status:** Accepted
- **Area:** Pay
- **From:** Change 12 – Employee pay, project budgets and labour cost (commit `062a78f`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Pay** area, recorded during Change 12 – Employee pay, project budgets and labour cost. It affects these parts of the specification: B.3, D-92.

## Decision

**Only admins see or change pay** (`can_manage_pay`). Admin → Employees: the employee page shows a read-only Pay line and links to `/admin/…/pay/` — current pay, the history (corrections marked), **Add pay change** (the form suggests salary ÷ 2,080 with "Use it"); nothing is ever deleted (PayRecord has no admin of its own). Pay is not in the employee list, the employee CSV, the employee import or the Profile. **Pay CSV** (admin-only, from the employee list): Export = every record (employee_code, pay_type, annual_salary, hourly_rate, effective_from; formula-safe; EXPORT audit row); Import = the same columns, checked like the employee import (preview, line-numbered errors, all-or-nothing, two rows for one person and date refused), **only adds** records (identical = unchanged, same date with other values = correction), each audited. Pay amounts never appear in logs, error messages or `str()`; outside Admin only hourly rates and costs appear, on Project budget (D-170).

## Consequences

- **Checked by:** [T-259](../testing.md#t-259), [T-260](../testing.md#t-260), [T-270](../testing.md#t-270)
- **Cited in code:** [`apps/compensation/admin.py`](../../apps/compensation/admin.py), [`apps/compensation/apps.py`](../../apps/compensation/apps.py), [`apps/compensation/models.py`](../../apps/compensation/models.py), [`apps/compensation/services/access.py`](../../apps/compensation/services/access.py), [`apps/compensation/services/pay.py`](../../apps/compensation/services/pay.py), [`apps/compensation/services/pay_import.py`](../../apps/compensation/services/pay_import.py), [`apps/reports/apps.py`](../../apps/reports/apps.py), [`config/settings/production.py`](../../config/settings/production.py), [`tests/compensation/integration/test_pay.py`](../../tests/compensation/integration/test_pay.py), [`tests/e2e/test_reports.py`](../../tests/e2e/test_reports.py)
- **Related decisions:** [D-170](D-170-reports-project-budget-who-sees-what.md)
