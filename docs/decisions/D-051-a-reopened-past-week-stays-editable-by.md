# D-51: A reopened past week stays editable by its employee until reopen_until

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-8/FR-9.

## Decision

A reopened past week stays editable by its employee until `reopen_until`; D-33 only stops future weeks. Employee saves in a REOPENED week write an UPDATE audit row with before/after entries.

## Consequences

- **Checked by:** [T-86](../testing.md#t-86)
- **Cited in code:** [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py)
- **Related decisions:** [D-33](D-033-employees-can-open-only-the-current-week.md)
