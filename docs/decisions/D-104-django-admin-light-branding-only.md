# D-104: Django Admin: light branding only

- **Status:** Accepted
- **Area:** UI
- **From:** Change 1 – Modern UI (commit `7f19f32`)
- **Recorded:** 2026-10-24

## Context

A decision in the **UI** area, recorded during Change 1 – Modern UI. It affects these parts of the specification: B.4 FR-10.

## Decision

**Django Admin: light branding only.** `site_header`/`site_title` = "Timesheets Admin"; `templates/admin/base_site.html` sets the admin's own colour variables (primary, header, breadcrumbs) to the accent and slate tokens in light mode and makes the site name dark. The admin's pages and dark mode are not restyled.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/directory/admin_site.py`](../../apps/directory/admin_site.py), [`templates/admin/base_site.html`](../../templates/admin/base_site.html)
