# D-117: No data conversion

- **Status:** Accepted
- **Area:** Data
- **From:** Change 3 – Sunday-to-Saturday week (commit `39485cd`)
- **Recorded:** 2026-10-24

## Context

A decision in the **Data** area, recorded during Change 3 – Sunday-to-Saturday week. It affects these parts of the specification: B.7, D-27, D.3.

## Decision

**No data conversion**: there is no data migration and no schema change (`week_start` stays a date; comments only). Existing Monday-week databases must be rebuilt by the owner (D.3 "Start over"). `seed_demo` creates Sunday weeks, history aligned to whole pay periods (D-27) with the current week empty, and the same scenarios (dev1/dev2 period pending, one rejected period, one open change request, one manager edit, exported/paid batches and one correction); decisions stay on Mondays, exports on Fridays and recent hires on Wednesdays.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Related decisions:** [D-27](D-027-seed-history-is-aligned-to-pay-periods.md)
