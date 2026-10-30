# D-27: Seed history is aligned to pay periods

- **Status:** Accepted
- **Area:** Data
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Data** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.7, C.4 P2.

## Decision

Seed history is aligned to pay periods: the 6 completed periods before the current one (26 with `--large`), plus week 1 of the current period when today is in its week 2 — 12 or 13 weeks. The current week is left empty.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/directory/services/demo/__init__.py`](../../apps/directory/services/demo/__init__.py), [`scripts/visual_review/test_screenshots.py`](../../scripts/visual_review/test_screenshots.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py)
