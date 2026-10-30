# D-18: PROJECT entries must have an active project

- **Status:** Accepted
- **Area:** Data
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Data** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.6, B.9, C.4 P5.

## Decision

PROJECT entries must have an active project; all other categories must have no project.

## Consequences

- **Checked by:** [T-67](../testing.md#t-67), [T-195](../testing.md#t-195)
- **Cited in code:** [`apps/directory/services/demo/constants.py`](../../apps/directory/services/demo/constants.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/grid_rows.py`](../../apps/timesheets/services/grid_rows.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py), [`tests/timesheets/unit/test_validation.py`](../../tests/timesheets/unit/test_validation.py)
