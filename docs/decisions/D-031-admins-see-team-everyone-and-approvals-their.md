# D-31: Admins see Team (everyone) and Approvals (their direct reports plus employees with no…

- **Status:** Accepted
- **Area:** Roles
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Roles** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.1, B.3, C.4 P4/P7/P10.

## Decision

Admins see **Team** (everyone) and **Approvals** (their direct reports plus employees with no manager, never themselves), even if they manage nobody. Managers see Team and Approvals for their own reports. Replaces "only for managers" in the C.4 Phase 4 prompt (B.1 row 14, B.3, D-11).

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/directory/services/permissions.py`](../../apps/directory/services/permissions.py)
- **Related decisions:** [D-11](D-011-nobody-can-ever-approve-their-own-timesheet.md)
