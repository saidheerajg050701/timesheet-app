# D-145: The secret key can't stay the example

- **Status:** Accepted
- **Area:** Setup
- **From:** README & first-run checks (commit `e17cc7d`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Setup** area, recorded during README & first-run checks. It affects these parts of the specification: B.10, D-96.

## Decision

**The secret key can't stay the example.** A system check (`apps/directory/checks.py`, run before runserver, migrate, seed_demo and every command) flags a `SECRET_KEY` equal to the `.env.example` value or shorter than 50 characters (Django's own deploy-check length): a **warning** (`directory.W001`) while `DEBUG` is on, an **error** (`directory.E001`) with `DEBUG` off, which stops the app. The message says which problem it is and how to generate a key; it never shows the key.

## Consequences

- **Checked by:** [T-225](../testing.md#t-225)
- **Cited in code:** [`apps/directory/apps.py`](../../apps/directory/apps.py), [`apps/directory/checks.py`](../../apps/directory/checks.py), [`tests/site/test_first_run_checks.py`](../../tests/site/test_first_run_checks.py)
