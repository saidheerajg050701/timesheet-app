# D-128: Change 6 – Optional reason on time entries

- **Status:** Accepted
- **Area:** Timesheet
- **From:** Change 6 – Optional reason on time entries (commit `23439ce`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Timesheet** area, recorded during Change 6 – Optional reason on time entries. It affects these parts of the specification: B.4 FR-8, B.6.

## Decision

**Change 6 – Optional reason on time entries** (supersedes the "required reason" of D-36 and the reason rule in D-49, D-107, D-127 and B.4 FR-8). The Reason field stays in every time-slot dialog (employee grid and Edit directly) but may be left empty for work, Break and leave; an empty or spaces-only reason is saved as blank (`""`); at most 255 characters is still checked. Read-only cell dialogs (submitted, locked and approved weeks, change requests, approvals, Team week view) show the Reason column only when at least one of the cell's slots has a reason; a slot without one shows an empty cell there. All other entry rules are unchanged; an entry with nothing typed is still ignored and one with only a reason still needs its times or hours. **Still required:** a change request's reason ("Explain what needs to change.") and a rejection comment (D-07). `TimeEntry.reason` gets `blank=True` in migration `timesheets/0005` (no database column changes). The demo data still gives every row a reason.

## Consequences

- **Checked by:** [T-74](../testing.md#t-74), [T-84](../testing.md#t-84), [T-187](../testing.md#t-187), [T-188](../testing.md#t-188), [T-189](../testing.md#t-189), [T-190](../testing.md#t-190), [T-199](../testing.md#t-199)
- **Cited in code:** [`apps/directory/services/demo/constants.py`](../../apps/directory/services/demo/constants.py), [`apps/timesheets/grid.py`](../../apps/timesheets/grid.py), [`apps/timesheets/models.py`](../../apps/timesheets/models.py), [`apps/timesheets/services/validation.py`](../../apps/timesheets/services/validation.py), [`tests/timesheets/unit/test_validation.py`](../../tests/timesheets/unit/test_validation.py)
- **Related decisions:** [D-07](D-007-reject-sets-both-weeks-to-reopened-with.md), [D-36](D-036-every-row-has-a-date-category-project.md), [D-49](D-049-edit-directly.md), [D-107](D-107-cells-and-slots.md), [D-127](D-127-easier-multiple-time-slots.md)
