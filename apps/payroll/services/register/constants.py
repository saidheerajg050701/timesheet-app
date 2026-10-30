"""Register statuses and line kinds (D-132–D-136)."""

from apps.payroll.models import PayrollRegisterLine

OPEN, READY = "OPEN", "READY"  # worked out live; FINALIZED and PAID are saved
BACKFILL_ACTOR = "build_registers"
LATE_WEEK, ADJUSTMENT = "LATE_WEEK", "ADJUSTMENT"
Line = PayrollRegisterLine.Status
