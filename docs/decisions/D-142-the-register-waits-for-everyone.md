# D-142: The register waits for everyone

- **Status:** Accepted
- **Area:** Payroll
- **From:** Change 9 – Managers decide everyone (commit `0f34b45`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Payroll** area, recorded during Change 9 – Managers decide everyone. It affects these parts of the specification: B.4 FR-11.

## Decision

**The register waits for everyone** (supersedes the deadline part of D-133 and the 0.00 lines of D-134). READY only when the period has ended, **every person who must be approved is APPROVED**, no change request is open on its weeks, and every approved week has its payroll record. The approval deadline is only the "Approve by …" reminder and the Overdue badge. Finalize & export is refused on the server until READY, so there are no 0.00 lines; "Missed – not submitted" / "Waiting for manager approval" remain only on registers saved before. While OPEN the period page shows only progress, the deadline and who is pending — no register table, week records, Finalize or downloads (week records still show for periods exported before registers). Carry-forward is unchanged: corrections after finalizing (D-136) and anything that becomes approvable afterwards (e.g. a new hire back-dated into the period). Before finalizing, a re-approved week simply replaces the old one in the register. Saved registers never change; `build_registers` / `sync_payroll` still only build registers for earlier exports.

## Consequences

- **Checked by:** [T-114](../testing.md#t-114), [T-205](../testing.md#t-205), [T-207](../testing.md#t-207), [T-208](../testing.md#t-208), [T-222](../testing.md#t-222), [T-224](../testing.md#t-224)
- **Cited in code:** [`apps/payroll/services/register/__init__.py`](../../apps/payroll/services/register/__init__.py), [`apps/payroll/services/register/state.py`](../../apps/payroll/services/register/state.py), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`tests/conftest.py`](../../tests/conftest.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py), [`tests/e2e/test_approvals.py`](../../tests/e2e/test_approvals.py), [`tests/e2e/test_payroll.py`](../../tests/e2e/test_payroll.py), [`tests/payroll/integration/test_adjustments.py`](../../tests/payroll/integration/test_adjustments.py), [`tests/payroll/integration/test_payroll_pages.py`](../../tests/payroll/integration/test_payroll_pages.py), [`tests/payroll/integration/test_payroll_register.py`](../../tests/payroll/integration/test_payroll_register.py), [`tests/timesheets/integration/test_manager_decisions.py`](../../tests/timesheets/integration/test_manager_decisions.py)
- **Related decisions:** [D-133](D-133-approval-deadline-and-ready.md), [D-134](D-134-register-lines.md), [D-136](D-136-carry-forward-with-registers.md)
