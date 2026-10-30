# D-96: DEBUG off for daily use

- **Status:** Accepted
- **Area:** Hardening
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-24

## Context

A decision in the **Hardening** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.10, D.2.

## Decision

**DEBUG off for daily use**: `.env.example` has `DJANGO_DEBUG=False`. With DEBUG off the vendored `/static/` files are served by a URL rule using `django.contrib.staticfiles.views.serve(insecure=True)` (open to anonymous users so the login page has its CSS) — acceptable for a local single-machine app with no build step and no extra package. Friendly `404.html` (site layout) and `500.html` (plain HTML, no context or database) never show code or settings. DEBUG=True still works for development.

## Consequences

- **Checked by:** [T-156](../testing.md#t-156)
- **Cited in code:** [`config/settings/production.py`](../../config/settings/production.py), [`config/urls.py`](../../config/urls.py), [`templates/500.html`](../../templates/500.html), [`tests/site/test_hardening.py`](../../tests/site/test_hardening.py)
