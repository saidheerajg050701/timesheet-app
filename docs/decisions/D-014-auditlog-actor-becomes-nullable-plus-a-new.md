# D-14: AuditLog.actor becomes nullable, plus a new field system_actor (e.g

- **Status:** Accepted
- **Area:** Audit
- **From:** Decisions log after the spec review (commit `93226f6`)
- **Recorded:** 2026-10-21

## Context

A decision in the **Audit** area, recorded during Decisions log after the spec review. It affects these parts of the specification: B.6, B.7, C.4 P2/P8.

## Decision

`AuditLog.actor` becomes nullable, plus a new field `system_actor` (e.g. `"seed_demo"`, `"sync_payroll"`) used when no person is acting. Exactly one of the two must be set.

## Consequences

- **Checked by:** [T-52](../testing.md#t-52), [T-57](../testing.md#t-57), [T-106](../testing.md#t-106)
- **Cited in code:** [`apps/audit/models.py`](../../apps/audit/models.py), [`apps/audit/services/log.py`](../../apps/audit/services/log.py), [`tests/audit/unit/test_audit.py`](../../tests/audit/unit/test_audit.py), [`tests/directory/integration/test_seed_demo.py`](../../tests/directory/integration/test_seed_demo.py)
