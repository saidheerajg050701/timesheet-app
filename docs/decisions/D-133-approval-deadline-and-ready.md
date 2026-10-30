# D-133: Approval deadline and READY

- **Status:** Accepted — later updated by D-142
- **Area:** Payroll
- **From:** Change 8 – Pay Period Register (commit `85f22e2`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Payroll** area, recorded during Change 8 – Pay Period Register. It affects these parts of the specification: B.4 FR-7, FR-11 *Superseded in part by D-142: the deadline no longer makes a register READY; it stays as the reminder and the Overdue badge.*.

## Decision

**Approval deadline and READY.** New settings `APPROVAL_DEADLINE_DAYS` (default 2) and `APPROVAL_DEADLINE_TIME` (default 12:00): managers approve a period by that many days after its last day (Saturday), company time — Monday 12:00 by default. The Approvals page shows "Approve by …" and an **Overdue** badge on rows not approved after it. A register is **READY** when the period has ended, payroll is in sync for it (every approved week has its record, D-65), and either everyone who must be approved is approved with no open change request on the period's weeks, or the deadline has passed. Before that "Finalize & export" is disabled and refused on the server — no early finalize.

## Consequences

- **Checked by:** [T-203](../testing.md#t-203), [T-205](../testing.md#t-205), [T-216](../testing.md#t-216)
- **Cited in code:** [`apps/payroll/services/register/__init__.py`](../../apps/payroll/services/register/__init__.py), [`apps/payroll/services/register/constants.py`](../../apps/payroll/services/register/constants.py), [`apps/payroll/services/register/state.py`](../../apps/payroll/services/register/state.py), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`apps/timesheets/services/pending.py`](../../apps/timesheets/services/pending.py), [`apps/timesheets/templatetags/timesheet_tags.py`](../../apps/timesheets/templatetags/timesheet_tags.py), [`apps/timesheets/views/approvals.py`](../../apps/timesheets/views/approvals.py), [`config/settings/base.py`](../../config/settings/base.py), [`tests/e2e/test_payroll.py`](../../tests/e2e/test_payroll.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py)
- **Related decisions:** [D-65](D-065-two-databases-fixed-order.md)
- **Updated later by:** [D-142](D-142-the-register-waits-for-everyone.md)
