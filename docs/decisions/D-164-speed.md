# D-164: Speed

- **Status:** Accepted
- **Area:** Reports
- **From:** Change 11 – Reports → Project hours (commit `23fcc6b`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Reports** area, recorded during Change 11 – Reports → Project hours. It affects these parts of the specification: D-86.

## Decision

**Speed.** The report reads the database a fixed number of times whatever the number of people or weeks (9 for a manager or admin, 7 for one's own report): the hierarchy, the people with team and manager, one entries query joined with each week's status, projects, tasks, the chosen projects and manager, and the manager choices; everything else is worked out in memory. Measured with `seed_demo --large` (492 people, 465 758 entries, on a test database): HR's page 0.18 s for the last pay period, 0.38 s for 12 weeks, 1.3 s for 52 weeks; a director (216 people) 0.08 / 0.15 / 0.58 s; CSV for everyone 0.17 / 0.6 / 2.6 s; the Excel workbook 1.3 / 6 / 27 s (about 4 million cells for a whole year of everyone — the CSV is the quick way to get that much). `time_project_report <email> [--period … --hours …]` measures it on any database without writing anything.

## Consequences

- **Checked by:** [T-251](../testing.md#t-251)
- **Cited in code:** [`apps/reports/apps.py`](../../apps/reports/apps.py), [`apps/reports/management/commands/time_project_report.py`](../../apps/reports/management/commands/time_project_report.py), [`apps/reports/services/project_report/__init__.py`](../../apps/reports/services/project_report/__init__.py), [`apps/reports/services/project_report/aggregate.py`](../../apps/reports/services/project_report/aggregate.py), [`apps/reports/services/project_report/queries.py`](../../apps/reports/services/project_report/queries.py), [`apps/reports/services/report_files.py`](../../apps/reports/services/report_files.py), [`apps/reports/views.py`](../../apps/reports/views.py), [`tests/reports/integration/test_project_report.py`](../../tests/reports/integration/test_project_report.py)
