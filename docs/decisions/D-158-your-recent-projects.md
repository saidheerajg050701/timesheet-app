# D-158: "Your recent projects"

- **Status:** Accepted
- **Area:** Grid
- **From:** Change 10b – Project I-codes and project search (commit `8c00c54`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Grid** area, recorded during Change 10b – Project I-codes and project search. It affects these parts of the specification: B.4 FR-3.

## Decision

**"Your recent projects"**: only while the search box is empty, the **week owner's** active projects with entries in the **4 weeks before the week being edited** (not the week itself), sorted by I-code, then "All active projects" (the others), sorted by I-code. In Edit directly and the Approvals edit the owner is the employee, not the manager. Typing shows only "Matching projects", sorted by I-code.

## Consequences

- **Checked by:** [T-242](../testing.md#t-242)
- **Cited in code:** [`apps/projects/services/projects.py`](../../apps/projects/services/projects.py), [`apps/projects/templates/projects/_project_options.html`](../../apps/projects/templates/projects/_project_options.html), [`apps/timesheets/views/requests.py`](../../apps/timesheets/views/requests.py), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py), [`tests/projects/integration/test_projects.py`](../../tests/projects/integration/test_projects.py)
