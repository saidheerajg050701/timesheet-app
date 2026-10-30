# D-46: A change request can be raised only by the employee, on their own week, when its…

- **Status:** Accepted
- **Area:** Change request
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Change request** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-9, B.6, C.4 P6.

## Decision

A change request can be raised only by the employee, on their own week, when its effective status is SUBMITTED, LOCKED or APPROVED — never DRAFT, NOT_STARTED, REOPENED or future weeks. At most one OPEN request per week (service check + partial unique constraint `one_open_request_per_week`). Raising on a missed week with no timesheet creates that week as LOCKED.

## Consequences

- **Checked by:** [T-81](../testing.md#t-81)
- **Cited in code:** [`apps/directory/services/demo/writing.py`](../../apps/directory/services/demo/writing.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py)
