# D-36: Every row has a date, category, project (Project work only, D-18) and a required…

- **Status:** Accepted — later updated by D-128
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-8, B.6.

## Decision

Every row has a date, category, project (Project work only, D-18) and a **required reason** (max 255 characters; *the reason is optional since D-128*). `TimeEntry.notes` is renamed to `reason`.

## Consequences

- **Checked by:** [T-74](../testing.md#t-74)
- **Cited in code:** [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/timesheets/migrations/0002_entry_times_reason_break.py`](../../apps/timesheets/migrations/0002_entry_times_reason_break.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py), [`tests/timesheets/unit/test_validation.py`](../../tests/timesheets/unit/test_validation.py)
- **Related decisions:** [D-18](D-018-project-entries-must-have-an-active-project.md), [D-128](D-128-optional-reason-on-time-entries.md)
- **Updated later by:** [D-128](D-128-optional-reason-on-time-entries.md)
