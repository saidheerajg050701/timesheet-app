# D-156: Migration timesheets/0008_project_i_codes

- **Status:** Accepted
- **Area:** Data
- **From:** Change 10b – Project I-codes and project search (commit `8c00c54`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Data** area, recorded during Change 10b – Project I-codes and project search. It affects these parts of the specification: B.6.

## Decision

**Migration `timesheets/0008_project_i_codes`** (for a database built before Change 10b): adds `number`, renames, then makes `number` required. `PRJ-<number>` keeps its number when that I-number is free; any other code (odd codes like "PILOT", lowercase, or a number already taken) gets the next free number after the highest, in code order; each rename is printed ("Project PRJ-001 → I-001"); it never stops. Time entries and allowed tasks link to projects by id, so they don't change; **audit rows are never edited** and none are added (old rows keep the old code). Reverse: back to `PRJ-<number>` (other old codes are not kept — there is no previous-code field). Because this is still demo data, the agreed path is to rebuild it (backup, move both databases aside, migrate, `seed_demo`) so no PRJ code remains anywhere.

## Consequences

- **Checked by:** [T-240](../testing.md#t-240)
- **Cited in code:** [`apps/projects/services/projects.py`](../../apps/projects/services/projects.py), [`apps/timesheets/migrations/0008_project_i_codes.py`](../../apps/timesheets/migrations/0008_project_i_codes.py), [`tests/projects/integration/test_projects.py`](../../tests/projects/integration/test_projects.py)
