# D-12: Roles add up

- **Status:** Accepted
- **Area:** Roles
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Roles** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.1, B.3, B.4 FR-11, B.9.

## Decision

Roles add up. Payroll users are also employees (own timesheet, analytics, change requests). The payroll flag only adds `/payroll/` and never grants access to other people's timesheet details. A payroll user who is also a manager gets normal manager rights for their own tree.

## Consequences

- **Checked by:** [T-62](../testing.md#t-62), [T-63](../testing.md#t-63), [T-111](../testing.md#t-111), [T-126](../testing.md#t-126)
- **Cited in code:** [`apps/directory/services/permissions.py`](../../apps/directory/services/permissions.py), [`apps/payroll/services/register/__init__.py`](../../apps/payroll/services/register/__init__.py), [`apps/payroll/views.py`](../../apps/payroll/views.py), [`tests/analytics/integration/test_team.py`](../../tests/analytics/integration/test_team.py), [`tests/directory/unit/test_permissions.py`](../../tests/directory/unit/test_permissions.py), [`tests/payroll/integration/test_payroll_pages.py`](../../tests/payroll/integration/test_payroll_pages.py), [`tests/site/test_layout.py`](../../tests/site/test_layout.py)
