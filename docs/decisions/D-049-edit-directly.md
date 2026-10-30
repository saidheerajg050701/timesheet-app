# D-49: Edit directly

- **Status:** Accepted — later updated by D-128
- **Area:** Change request
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-23

## Context

A decision in the **Change request** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.4 FR-9, B.5, B.9 #10.

## Decision

**Edit directly** uses the Phase 5b validation for the week's employee (times, reason length — a reason is optional since D-128 —, no overlaps, Break rules, 24 h, employment dates, no Break-only/empty week). The week becomes SUBMITTED (first-time `submitted_at`/`is_late` only if never submitted). If it was in an APPROVED period, `approvals.reset_approval` sets the period to PENDING, its approved weeks to SUBMITTED and calls the payroll hook, in the same transaction (D-10). Audit UPDATE stores before/after status and entries with times and reasons.

## Consequences

- **Checked by:** [T-83](../testing.md#t-83), [T-84](../testing.md#t-84), [T-197](../testing.md#t-197)
- **Cited in code:** [`apps/timesheets/services/changes.py`](../../apps/timesheets/services/changes.py), [`apps/timesheets/views/__init__.py`](../../apps/timesheets/views/__init__.py), [`apps/timesheets/views/requests.py`](../../apps/timesheets/views/requests.py), [`tests/timesheets/integration/test_change_requests.py`](../../tests/timesheets/integration/test_change_requests.py)
- **Related decisions:** [D-10](D-010-periodapproval-is-the-source-of-truth.md), [D-128](D-128-optional-reason-on-time-entries.md)
- **Updated later by:** [D-128](D-128-optional-reason-on-time-entries.md)
