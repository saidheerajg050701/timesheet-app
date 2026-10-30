# D-52: is_late is decided by the first submission only

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-8, B.5.

## Decision

`is_late` is decided by the first submission only: an on-time week reopened and resubmitted stays on time; a missed week submitted later is late and stays late (refines D-08).

## Consequences

- **Checked by:** [T-87](../testing.md#t-87)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py)
- **Related decisions:** [D-08](D-008-when-a-reopen-window-unlock-or-reject.md)
