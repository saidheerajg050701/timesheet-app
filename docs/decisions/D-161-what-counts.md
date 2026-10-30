# D-161: What counts

- **Status:** Accepted
- **Area:** Reports
- **From:** Change 11 – Reports → Project hours (commit `23fcc6b`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Reports** area, recorded during Change 11 – Reports → Project hours. It affects these parts of the specification: B.4 FR-5, FR-6.

## Decision

**What counts.** **Project hours** = Project-work entries for the selected projects (all when none is chosen); per-project and per-task numbers are project-only, so they add up to project hours ("Task not recorded" is its own line). **Non-project time** = Meetings, Training, Other, always shown and **never filtered by project** (labelled so). **Total time** = project hours + non-project time — the same three figures in the Summary, per team, per manager group, per person, in the Excel and the CSV. **Break and leave never count**; leave (PTO, Sick, Holiday) is shown per person for context only. **Hours** filter by the week's stored status: Approved (default) / Approved + Submitted / Everything entered (draft, locked, reopened, submitted, approved); the CSV shows the effective status (`effective_status`). **Period**: this pay period, last pay period (default), last 4 / 12 weeks (ending with the current week), or custom dates widened to whole Sunday–Saturday weeks (calendar.py), at most 53 weeks; bad or reversed dates fall back to the last pay period with a message. **Projects** (`project=I-001&project=I-003`, chosen with the 10b search box, inactive projects included and marked; unknown codes left out with a message). All filters live in the address, so a link can be shared.

## Consequences

- **Checked by:** [T-246](../testing.md#t-246), [T-247](../testing.md#t-247)
- **Cited in code:** [`apps/projects/services/projects.py`](../../apps/projects/services/projects.py), [`apps/projects/static/projects/project_search.js`](../../apps/projects/static/projects/project_search.js), [`apps/projects/templates/projects/_project_options.html`](../../apps/projects/templates/projects/_project_options.html), [`apps/reports/apps.py`](../../apps/reports/apps.py), [`apps/reports/services/project_report/__init__.py`](../../apps/reports/services/project_report/__init__.py), [`apps/reports/services/project_report/aggregate.py`](../../apps/reports/services/project_report/aggregate.py), [`apps/reports/services/project_report/constants.py`](../../apps/reports/services/project_report/constants.py), [`apps/reports/services/project_report/filters.py`](../../apps/reports/services/project_report/filters.py), [`apps/reports/services/project_report/queries.py`](../../apps/reports/services/project_report/queries.py), [`apps/reports/services/project_report/rows.py`](../../apps/reports/services/project_report/rows.py), [`apps/reports/static/reports/report.js`](../../apps/reports/static/reports/report.js), [`apps/reports/views.py`](../../apps/reports/views.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/reports/integration/test_project_report.py`](../../tests/reports/integration/test_project_report.py)
