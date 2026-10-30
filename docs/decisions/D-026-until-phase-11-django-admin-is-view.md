# D-26: Until Phase 11, Django Admin is view-only for every model (passwords shown only as a…

- **Status:** Accepted
- **Area:** Setup
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Setup** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-10, C.4 P2/P11.

## Decision

Until Phase 11, Django Admin is view-only for every model (passwords shown only as a masked Argon2 summary). Phase 11 adds editing, deactivate and password reset together with their audit rows — ended for directory data by D-87.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/directory/admin_base.py`](../../apps/directory/admin_base.py)
- **Related decisions:** [D-87](D-087-d-26-ends-for-directory-data-only.md)
