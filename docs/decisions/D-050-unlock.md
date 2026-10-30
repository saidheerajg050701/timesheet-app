# D-50: Unlock

- **Status:** Accepted
- **Area:** Change request
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Change request** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-9, B.5.

## Decision

**Unlock** sets REOPENED with `reopen_until` = the later of now + 48 h and the week's Saturday 12:00 (D-21); an APPROVED week is first reset through `approvals.unlock_week`. An unused window makes the week LOCKED (read-time, D-08, D-34).

## Consequences

- **Checked by:** [T-83](../testing.md#t-83)
- **Cited in code:** [`apps/timesheets/services/approvals.py`](../../apps/timesheets/services/approvals.py), [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py)
- **Related decisions:** [D-08](D-008-when-a-reopen-window-unlock-or-reject.md), [D-21](D-021-reopen-window.md), [D-34](D-034-locked-and-missed-are-worked-out-when.md)
