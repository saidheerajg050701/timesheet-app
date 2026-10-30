# D-86: Performance

- **Status:** Accepted
- **Area:** Team
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Team** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.9 #6, B.10.

## Decision

**Performance.** The reporting tree is built in memory from one `(id, manager_id)` query (cycle-safe; T-27/T-28 unchanged). The team page and dashboard load people, timesheets, entries (as light read-only `EntryFacts` records via `values_list`, not model objects), projects and approvals in a fixed number of queries, whatever the tree size or range (T-132); measured in the test DB with ~500 people and 26 weeks of entries: CEO 0.3 s (12 weeks) / 0.6 s (26 weeks). `uv run python manage.py time_team_page <email> [--weeks 4|12|26] [--direct]` renders `/team/` in memory (no session, no writes) and prints the time and query count.

## Consequences

- **Checked by:** [T-132](../testing.md#t-132)
- **Cited in code:** [`apps/analytics/management/commands/time_team_page.py`](../../apps/analytics/management/commands/time_team_page.py), [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/analytics/services/team.py`](../../apps/analytics/services/team.py), [`apps/analytics/views/team.py`](../../apps/analytics/views/team.py), [`apps/directory/services/permissions.py`](../../apps/directory/services/permissions.py), [`tests/analytics/integration/test_team.py`](../../tests/analytics/integration/test_team.py), [`tests/analytics/unit/test_team_metrics.py`](../../tests/analytics/unit/test_team_metrics.py)
