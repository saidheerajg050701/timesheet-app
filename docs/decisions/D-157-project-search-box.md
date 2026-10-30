# D-157: Project search box

- **Status:** Accepted
- **Area:** Grid
- **From:** Change 10b – Project I-codes and project search (commit `8c00c54`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Grid** area, recorded during Change 10b – Project I-codes and project search. It affects these parts of the specification: B.4 FR-3, D-152.

## Decision

**Project search box** in "+ Add row" and ⋮ Change row (employee grid, Edit directly, Approvals edit), replacing the Project drop-down. **Matching** (one function, `projects.search_projects`): active projects whose I-code or name contains the typed text, partial and case-insensitive ("i-00", "001", "portal"), sorted by I-code; inactive projects never appear. **Lists** come from the server (`_project_options.html`): headed groups, or "No matching project". Each editor has its own list address under its own URL — `timesheets/<week>/projects/` (own open week; 403 when locked), `approvals/requests/<id>/projects/` (Edit directly, the request's handler) and `approvals/<period>/<code>/weeks/<week>/projects/` (the approver) — using that editor's existing permission check (GET only). **Accessible:** a labelled `role="combobox"` input with `aria-autocomplete="list"`, `aria-expanded`, `aria-controls` and `aria-activedescendant`; a `role="listbox"` of `role="option"` items ("I-001 Customer Portal") in labelled groups; a polite status announcing "3 projects" / "No matching project"; ↑/↓ move, Enter chooses (never submits the week), Esc closes the list (a second Esc closes the dialog), Tab or leaving the box closes it; click or tap chooses. The list is part of the dialog (never clipped), scrolls, and fits a phone. Choosing fills the box and a hidden `new-project` field and refreshes the Task list (D-152); typing again clears the choice ("Choose a project."). ⋮ Change row opens on the row's own project. `grid.js` only, no new library; the server still refuses an unknown or inactive project (`target_problem`, `validate_entries`).

## Consequences

- **Checked by:** [T-241](../testing.md#t-241), [T-243](../testing.md#t-243)
- **Cited in code:** [`apps/projects/services/projects.py`](../../apps/projects/services/projects.py), [`apps/projects/static/projects/project_search.js`](../../apps/projects/static/projects/project_search.js), [`apps/projects/templates/projects/_project_combo.html`](../../apps/projects/templates/projects/_project_combo.html), [`apps/projects/templates/projects/_project_options.html`](../../apps/projects/templates/projects/_project_options.html), [`apps/timesheets/static/timesheets/grid.js`](../../apps/timesheets/static/timesheets/grid.js), [`apps/timesheets/templates/timesheets/_grid.html`](../../apps/timesheets/templates/timesheets/_grid.html), [`apps/timesheets/views/approvals.py`](../../apps/timesheets/views/approvals.py), [`apps/timesheets/views/requests.py`](../../apps/timesheets/views/requests.py), [`apps/timesheets/views/weeks.py`](../../apps/timesheets/views/weeks.py), [`static/css/theme.css`](../../static/css/theme.css), [`tests/e2e/helpers.py`](../../tests/e2e/helpers.py), [`tests/e2e/test_timesheets.py`](../../tests/e2e/test_timesheets.py), [`tests/projects/integration/test_projects.py`](../../tests/projects/integration/test_projects.py), [`tests/timesheets/integration/test_row_actions.py`](../../tests/timesheets/integration/test_row_actions.py)
- **Related decisions:** [D-152](D-152-grid-rows-per-category-project-task.md)
