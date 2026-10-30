# D-131: Static files are revalidated on every page load

- **Status:** Accepted
- **Area:** Hardening
- **From:** Change 7 – Edit or delete a whole row (commit `23439ce`)
- **Recorded:** 2026-10-26

## Context

A decision in the **Hardening** area, recorded during Change 7 – Edit or delete a whole row. It affects these parts of the specification: B.10, D-96.

## Decision

**Static files are revalidated on every page load.** `/static/` (D-96) answers with `Cache-Control: no-cache`; an unchanged file answers `304 Not Modified` to the browser's If-Modified-Since, so this costs almost nothing. Reason: before, files were served with only Last-Modified, so Chrome reused cached copies by its own heuristic (about a tenth of the file's age); after an update a page could run with the previous `grid.js` and `theme.css` — found in Change 7, where the new ⋮ menu then sat under the next row and its items did nothing. Chosen over versioned file names (`ManifestStaticFilesStorage` needs `collectstatic`, which this app doesn't use) and a hand-bumped `?v=` (easy to forget). After this change, one hard reload (⌘⇧R) clears copies a browser cached earlier.

## Consequences

- **Checked by:** [T-201](../testing.md#t-201), [T-202](../testing.md#t-202)
- **Cited in code:** [`config/urls.py`](../../config/urls.py), [`tests/site/test_ui_theme.py`](../../tests/site/test_ui_theme.py)
- **Related decisions:** [D-96](D-096-debug-off-for-daily-use.md)
