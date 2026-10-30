# D-101: Layout

- **Status:** Accepted
- **Area:** UI
- **From:** Change 1 – Modern UI (commit `7f19f32`)
- **Recorded:** 2026-10-24

## Context

A decision in the **UI** area, recorded during Change 1 – Modern UI. It affects these parts of the specification: B.8.

## Decision

**Layout.** Light top bar with a 1 px bottom border: active page as a tinted pill (`aria-current="page"`), pill badges, and a user block with an initials avatar, name · Employee ID and title · team; Log out stays a POST button. Pages: a page header (title, short subtitle, actions on the right), content in cards, max width 1200 px (1400 px for Team, Approvals and Payroll). Tables: soft header, row hover, comfortable rows; long tables (timesheets list, approvals, team, payroll) keep their header visible in a 70vh scroll box on laptop screens; on narrow windows tables scroll sideways inside their card and the page itself never does. Login, sign-up, profile, account locked, 403, 404 and 500 are centered cards with the app name (500 stays standalone HTML with the token values inline, D-96).

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`static/css/theme.css`](../../static/css/theme.css)
- **Related decisions:** [D-96](D-096-debug-off-for-daily-use.md)
