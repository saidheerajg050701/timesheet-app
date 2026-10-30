# D-81: Who is on /team/: whole tree = the viewer's reporting tree, or everyone for an admin

- **Status:** Accepted
- **Area:** Team
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Team** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-6, B.3.

## Decision

Who is on `/team/`: **whole tree** = the viewer's reporting tree, or **everyone** for an admin; **direct reports** = only people whose manager is the viewer. The viewer is never listed; the payroll flag adds nothing (D-12). An optional team filter narrows the list (an unknown value = all teams). People with no employed day in the range are left out; inactive employees appear only with a timesheet in the range (as D-54).

## Consequences

- **Checked by:** [T-125](../testing.md#t-125), [T-127](../testing.md#t-127), [T-129](../testing.md#t-129)
- **Cited in code:** [`apps/analytics/services/team.py`](../../apps/analytics/services/team.py), [`apps/analytics/views/team.py`](../../apps/analytics/views/team.py), [`apps/directory/services/permissions.py`](../../apps/directory/services/permissions.py), [`tests/analytics/integration/test_team.py`](../../tests/analytics/integration/test_team.py)
- **Related decisions:** [D-12](D-012-roles-add-up.md), [D-54](D-054-approvals-lists-the-employees-the-viewer-may.md)
