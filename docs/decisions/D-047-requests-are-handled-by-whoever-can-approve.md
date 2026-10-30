# D-47: Requests are handled by whoever can_approve the week's employee

- **Status:** Accepted
- **Area:** Change request
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Change request** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.3, B.8, C.4 P6.

## Decision

Requests are handled by whoever `can_approve` the week's employee: the direct manager, or admins for employees with no manager; nobody handles their own (D-11, D-31). The inbox `/approvals/requests/` (`request_inbox`) is new — Phase 4 had no placeholder for it; `/requests/` (`requests`) lists the employee's own requests.

## Consequences

- **Checked by:** [T-82](../testing.md#t-82), [T-196](../testing.md#t-196)
- **Cited in code:** [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py), [`apps/timesheets/views/__init__.py`](../../apps/timesheets/views/__init__.py), [`apps/timesheets/views/requests.py`](../../apps/timesheets/views/requests.py)
- **Related decisions:** [D-11](D-011-nobody-can-ever-approve-their-own-timesheet.md), [D-31](D-031-admins-see-team-everyone-and-approvals-their.md)
