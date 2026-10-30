# D-102: One status badge component

- **Status:** Accepted
- **Area:** UI
- **From:** Change 1 – Modern UI (commit `7f19f32`)
- **Recorded:** 2026-10-24

## Context

A decision in the **UI** area, recorded during Change 1 – Modern UI. It affects these parts of the specification: B.5, B.8.

## Decision

**One status badge component**, `templates/includes/status_badge.html` (context: `status`, optional `label` and `badge_id`; included with `only`), plus `includes/week_badges.html` (a week's status with its Late / Missed / Change requested flags) and `timesheets/_flags.html` (approval flags). Every page that shows a week, pay period, change request or payroll status uses them. The `status_tone` filter (replacing `status_badge`) maps codes to tones: neutral (Not started, Not employed, Pending, In progress, Current, Superseded, Read-only, Not submitted yet), draft (grey), submitted (blue; also Exported), approved (green; also Paid, Unlocked, Edited), danger (red; Locked, Missed, Rejected, Missing days), reopened (violet), warning (amber; Late, Change requested, an open change request), info (cyan; Overtime). Soft background with dark text, always with the word, never colour alone.

## Consequences

- **Checked by:** [T-158](../testing.md#t-158)
- **Cited in code:** [`apps/timesheets/templates/timesheets/_flags.html`](../../apps/timesheets/templates/timesheets/_flags.html), [`apps/timesheets/templatetags/timesheet_tags.py`](../../apps/timesheets/templatetags/timesheet_tags.py), [`static/css/theme.css`](../../static/css/theme.css), [`templates/includes/status_badge.html`](../../templates/includes/status_badge.html), [`templates/includes/week_badges.html`](../../templates/includes/week_badges.html)
