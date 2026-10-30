# D-100: Change 1 – Modern UI: one theme stylesheet

- **Status:** Accepted
- **Area:** UI
- **From:** Change 1 – Modern UI (commit `7f19f32`)
- **Recorded:** 2026-10-24

## Context

A decision in the **UI** area, recorded during Change 1 – Modern UI. It affects these parts of the specification: B.8, B.10.

## Decision

**Change 1 – Modern UI: one theme stylesheet.** `static/css/theme.css`, loaded after the vendored Bootstrap 5.3.8 on every page (no CDN, no build step, no new package, no downloaded fonts). Design tokens as CSS variables (`--ts-*`): one accent `#2563eb`, slate neutral greys, status tones, spacing 4/8/12/16/24/32 px, radii 6/10/14 px, two soft shadows, 150 ms transitions; mapped onto Bootstrap's variables (`--bs-primary`, body font and colours, button, alert and focus-ring variables) so existing classes follow. System font stack `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`; tables use tabular figures with numbers right-aligned. One visible 3 px accent focus ring for keyboard users; `prefers-reduced-motion` switches transitions off. Text and badges meet WCAG AA (T-159). Behaviour, URLs, permissions, rules and the labels tests rely on are unchanged.

## Consequences

- **Checked by:** [T-157](../testing.md#t-157), [T-159](../testing.md#t-159)
- **Cited in code:** [`static/css/theme.css`](../../static/css/theme.css)
