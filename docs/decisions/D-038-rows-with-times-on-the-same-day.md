# D-38: Rows with times on the same day must not overlap, breaks included

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Timesheet** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-8, B.9.

## Decision

Rows with times on the same day must not overlap, breaks included; back-to-back rows (end = next start) are fine.

## Consequences

- **Checked by:** [T-73](../testing.md#t-73), [T-164](../testing.md#t-164), [T-184](../testing.md#t-184), [T-185](../testing.md#t-185), [T-194](../testing.md#t-194)
- **Cited in code:** [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`apps/timesheets/services/weeks.py`](../../apps/timesheets/services/weeks.py), [`tests/timesheets/unit/test_validation.py`](../../tests/timesheets/unit/test_validation.py)
