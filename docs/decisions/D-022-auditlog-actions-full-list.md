# D-22: AuditLog actions (full list)

- **Status:** Accepted
- **Area:** Audit
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-22

## Context

A decision in the **Audit** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.6, B.10, C.4 P8.

## Decision

AuditLog actions (full list): CREATE, UPDATE, DELETE, SUBMIT, APPROVE, REJECT, UNLOCK, PUBLISH, SUPERSEDE, EXPORT, PAY, SYNC. Publish, supersede, export, pay and sync each write an audit row.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`apps/audit/models.py`](../../apps/audit/models.py), [`apps/audit/services/log.py`](../../apps/audit/services/log.py)
