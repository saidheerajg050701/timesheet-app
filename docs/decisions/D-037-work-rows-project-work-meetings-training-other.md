# D-37: Work rows (Project work, Meetings, Training, Other) and Break rows have a start and…

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.1 row 15, B.4 FR-8, B.6, B.9.

## Decision

Work rows (Project work, Meetings, Training, Other) and Break rows have a start and end time ("login to logout" for that row) in 15-minute steps; end must be after start and the row cannot cross midnight (latest end 23:45). Hours are calculated from the times and stored as whole minutes.

## Consequences

- **Checked by:** [T-72](../testing.md#t-72), [T-76](../testing.md#t-76)
- **Cited in code:** [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/directory/services/demo/records.py`](../../apps/directory/services/demo/records.py), [`apps/timesheets/forms.py`](../../apps/timesheets/forms.py), [`apps/timesheets/migrations/0002_entry_times_reason_break.py`](../../apps/timesheets/migrations/0002_entry_times_reason_break.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py), [`apps/timesheets/templatetags/timesheet_tags.py`](../../apps/timesheets/templatetags/timesheet_tags.py), [`tests/timesheets/unit/test_validation.py`](../../tests/timesheets/unit/test_validation.py)
