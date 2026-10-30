# D-155: Change 10b – Project I-codes

- **Status:** Accepted
- **Area:** Data
- **From:** Change 10b – Project I-codes and project search (commit `8c00c54`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Data** area, recorded during Change 10b – Project I-codes and project search. It affects these parts of the specification: B.6, D-88.

## Decision

**Change 10b – Project I-codes.** A project's code is **"I-" + its number with at least 3 digits** (I-001 … I-999, I-1000), stored in `Project.code` (unique) with the number in `Project.number` (unique), and every project list, grid row order and charge-code table is sorted by number, so I-1000 follows I-999. The app assigns the code when a project is added (`projects.assign_code` inside `directory_admin.save_project`'s transaction): the next number after the highest ever used — projects are never deleted (D-87), so that is the highest existing number, inactive ones included; numbers are **never reused**, and codes are **never edited**. Admin → Projects → Add has no code field ("The I-code (I-001, I-002, …) is assigned when you save."); a posted code or number is ignored; the change page shows the code read-only. Still audited (CREATE with the I-code, D-88), still no delete, admins only. Charge codes follow: **I-001-DEV** (D-150).

## Consequences

- **Checked by:** [T-134](../testing.md#t-134), [T-238](../testing.md#t-238), [T-239](../testing.md#t-239)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/directory/services/demo/constants.py`](../../apps/directory/services/demo/constants.py), [`apps/directory/services/demo/projects.py`](../../apps/directory/services/demo/projects.py), [`apps/projects/admin.py`](../../apps/projects/admin.py), [`apps/projects/apps.py`](../../apps/projects/apps.py), [`apps/projects/models.py`](../../apps/projects/models.py), [`apps/projects/services/project_admin.py`](../../apps/projects/services/project_admin.py), [`apps/projects/services/projects.py`](../../apps/projects/services/projects.py), [`apps/timesheets/migrations/0008_project_i_codes.py`](../../apps/timesheets/migrations/0008_project_i_codes.py), [`tests/projects/integration/test_projects.py`](../../tests/projects/integration/test_projects.py)
- **Related decisions:** [D-87](D-087-d-26-ends-for-directory-data-only.md), [D-88](D-088-every-admin-add-change-goes-through-apps.md), [D-150](D-150-charge-code.md)
