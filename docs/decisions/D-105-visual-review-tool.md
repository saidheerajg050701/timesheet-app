# D-105: Visual review tool

- **Status:** Accepted
- **Area:** UI
- **From:** Change 1 – Modern UI (commit `7f19f32`)
- **Recorded:** 2026-10-24

## Context

A decision in the **UI** area, recorded during Change 1 – Modern UI. It affects these parts of the specification: B.11.

## Decision

**Visual review tool** (not part of `test_all.sh`): `SCREENSHOTS_DIR=<folder outside the repo> uv run pytest scripts/visual_review --browser-channel chrome`. It starts a live test server on the **test databases**, runs `seed_demo` there with a fixed clock (Wed 2026-10-21 10:00, also in the browser), logs in as dev1, eng.manager, payroll and hr, checks each page's status code and that the page never scrolls sideways, and saves full-page screenshots at 1440×900 and 390×844. It never touches `db.sqlite3` or `payroll.sqlite3`.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`scripts/visual_review/test_screenshots.py`](../../scripts/visual_review/test_screenshots.py)
