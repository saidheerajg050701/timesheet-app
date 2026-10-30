# D-153: Hours by task and by charge code

- **Status:** Accepted
- **Area:** Analytics
- **From:** Change 10 – Project tasks and charge codes (commit `22466dc`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Analytics** area, recorded during Change 10 – Project tasks and charge codes. It affects these parts of the specification: B.4 FR-5, FR-6, FR-11.

## Decision

**Hours by task and by charge code.** `metrics.hours_by_task` (largest first) and `hours_by_charge_code` (by project code, then task order) count Project work only; entries without a task are one **"Task not recorded"** line (last; its bar drawn in the muted colour, and its label says so). The dashboard and the Team page (summed over the selected people: `team_tasks`, `team_charge_codes`) get the cards "Hours by task" (bar chart + table) and "Hours by project + task" (table: charge code, project, task, hours); the project and category cards are unchanged. The task fields come with the entries query (a join), so the fixed query count of D-86 is unchanged. **Payroll is unchanged:** no task, project or charge code in payroll records, registers or CSVs.

## Consequences

- **Checked by:** [T-233](../testing.md#t-233), [T-234](../testing.md#t-234)
- **Cited in code:** [`apps/analytics/services/metrics.py`](../../apps/analytics/services/metrics.py), [`apps/analytics/services/team.py`](../../apps/analytics/services/team.py), [`apps/analytics/static/analytics/dashboard.js`](../../apps/analytics/static/analytics/dashboard.js), [`apps/analytics/static/analytics/team.js`](../../apps/analytics/static/analytics/team.js), [`apps/analytics/templates/analytics/parts/_tasks.html`](../../apps/analytics/templates/analytics/parts/_tasks.html), [`apps/projects/apps.py`](../../apps/projects/apps.py), [`apps/projects/models.py`](../../apps/projects/models.py), [`tests/projects/integration/test_tasks.py`](../../tests/projects/integration/test_tasks.py)
- **Related decisions:** [D-86](D-086-performance.md)
