# D-94: E2E tests

- **Status:** Accepted
- **Area:** Tests
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Tests** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.11, C.4 P12.

## Decision

**E2E tests** live in `tests/e2e/`, marked `e2e`, and run against pytest-django's `live_server` on the **test databases** (both, `transaction=True`) — never `db.sqlite3` or `payroll.sqlite3`. Data comes from factories in each test (not `seed_demo`). The clock is fixed with `time_machine` at Wed 2026-10-21 10:00 Chicago (`tick=True`) and moved with `move_to()` for deadline tests. Only Playwright `expect(...)` and explicit waits, never sleeps. One browser context per person; confirm dialogs are accepted. `DJANGO_ALLOW_ASYNC_UNSAFE=true` is set for e2e only (Playwright's sync API runs an event loop in the test thread). Catalogued as T-146–T-155.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`scripts/visual_review/test_screenshots.py`](../../scripts/visual_review/test_screenshots.py), [`tests/e2e/conftest.py`](../../tests/e2e/conftest.py), [`tests/e2e/helpers.py`](../../tests/e2e/helpers.py)
