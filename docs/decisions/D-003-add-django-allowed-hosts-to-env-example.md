# D-03: Add DJANGO_ALLOWED_HOSTS to .env.example (default 127.0.0.1,localhost).

- **Status:** Accepted
- **Area:** Setup
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Setup** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.1 `.env`, C.4 P1.

## Decision

Add `DJANGO_ALLOWED_HOSTS` to `.env.example` (default `127.0.0.1,localhost`).

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`config/settings/base.py`](../../config/settings/base.py)
