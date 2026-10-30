# D-40: Leave rows (PTO, Sick, Holiday) have hours only, without start or end times.

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.1 row 15, B.4 FR-8, B.6.

## Decision

Leave rows (PTO, Sick, Holiday) have hours only, without start or end times.

## Consequences

- **Checked by:** [T-76](../testing.md#t-76), [T-163](../testing.md#t-163)
- **Cited in code:** [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py), [`tests/timesheets/unit/test_validation.py`](../../tests/timesheets/unit/test_validation.py)
