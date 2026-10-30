# D-08: When a reopen window (unlock or reject, length per D-21) ends without resubmission,…

- **Status:** Accepted — later updated by D-52
- **Area:** Timesheet status
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Timesheet status** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.1, B.4 FR-8/FR-9, B.5, B.9, B.11 T-24.

## Decision

When a reopen window (unlock or reject, length per D-21) ends without resubmission, the week becomes LOCKED. A week submitted after its original deadline keeps `is_late = True`.

## Consequences

- **Checked by:** [T-87](../testing.md#t-87)
- **Cited in code:** [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/timesheets/services/calendar.py`](../../apps/timesheets/services/calendar.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py), [`tests/timesheets/unit/test_calendar.py`](../../tests/timesheets/unit/test_calendar.py)
- **Related decisions:** [D-21](D-021-reopen-window.md)
- **Updated later by:** [D-52](D-052-is-late-is-decided-by-the-first.md)
