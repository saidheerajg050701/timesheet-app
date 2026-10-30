# D-44: TimeEntry gets start_time, end_time and reason (renamed from notes) plus the BREAK…

- **Status:** Accepted
- **Area:** Data
- **From:** Version 1 (Phases 1–12)
- **Recorded:** 2026-10-22

## Context

A decision in the **Data** area, recorded during Version 1 (Phases 1–12). It affects these parts of the specification: B.6, B.7, D.3.

## Decision

`TimeEntry` gets `start_time`, `end_time` and `reason` (renamed from `notes`) plus the BREAK category in migration `timesheets/0002`. `seed_demo` creates realistic times, reasons and lunch breaks. Existing databases are migrated, never deleted, flushed or reseeded automatically; rebuild them with the D.3 "start over" steps.

## Consequences

- **Checked by:** [T-80](../testing.md#t-80)
- **Cited in code:** [`apps/directory/services/demo/history.py`](../../apps/directory/services/demo/history.py), [`apps/timesheets/migrations/0002_entry_times_reason_break.py`](../../apps/timesheets/migrations/0002_entry_times_reason_break.py)
