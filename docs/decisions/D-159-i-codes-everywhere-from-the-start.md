# D-159: I-codes everywhere from the start

- **Status:** Accepted
- **Area:** Data
- **From:** Change 10b – Project I-codes and project search (commit `8c00c54`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Data** area, recorded during Change 10b – Project I-codes and project search. It affects these parts of the specification: B.7.

## Decision

**I-codes everywhere from the start.** `seed_demo` creates its 8 projects through `assign_code` (I-001 Customer Portal … I-008 Legacy Billing (closed)), its tasks per project and per team are keyed by I-code, and all demo history, charge codes and audit rows use I-codes (the seed's project CREATE rows now also list the code). README, this guide (including the D-148–D-154 examples) and CLAUDE.md use I-codes in every example.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Related decisions:** [D-148](D-148-tasks.md), [D-149](D-149-allowed-tasks-per-project.md), [D-150](D-150-charge-code.md), [D-151](D-151-the-entry-rule-for-tasks.md), [D-152](D-152-grid-rows-per-category-project-task.md), [D-153](D-153-hours-by-task-and-by-charge-code.md), [D-154](D-154-demo-tasks-seed-demo.md)
