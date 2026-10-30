# D-154: Demo tasks (seed_demo)

- **Status:** Accepted
- **Area:** Data
- **From:** Change 10 – Project tasks and charge codes (commit `22466dc`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Data** area, recorded during Change 10 – Project tasks and charge codes. It affects these parts of the specification: B.7.

## Decision

**Demo tasks (seed_demo).** Each project allows a realistic set (I-001 Customer Portal: PLN, DES, DEV, TST, REL, SUP, DOC, MTG; I-005 Service Desk: SUP, DOC, TST, MTG; I-007 Internal Operations: PLN, DOC, MTG, SEC; …), recorded in its CREATE audit row. Each project entry is booked to a task its project allows that the person's team usually does (Platform DEV, TST, REL, MTG; Support SUP, DOC; Data DEV, PLN; People and Payroll DOC, MTG, PLN; …), falling back to any allowed task; the fixed random seed keeps it repeatable. Every seeded week still passes the rules (T-80).

## Consequences

- **Checked by:** [T-235](../testing.md#t-235)
- **Cited in code:** [`apps/directory/services/demo/constants.py`](../../apps/directory/services/demo/constants.py), [`apps/directory/services/demo/projects.py`](../../apps/directory/services/demo/projects.py), [`apps/projects/apps.py`](../../apps/projects/apps.py), [`apps/projects/models.py`](../../apps/projects/models.py), [`tests/projects/integration/test_tasks.py`](../../tests/projects/integration/test_tasks.py)
