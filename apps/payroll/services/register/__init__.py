"""Pay period registers (Change 8, D-132–D-137): one table per 2-week pay period, one line per
employee, with carry-forward columns.

While a period's register is not finalized its status is worked out live: OPEN until every
person who must be approved is approved (Change 9, D-142), then READY. "Finalize & export"
saves it once — one batch, frozen lines — and "Mark as paid" closes it. Every number
comes from the PayrollWeek and PayrollAdjustment records (their split from hours.py); nothing
is worked out a second way, and timesheet rows or reasons never appear here (D-12, D-122).

The package (D-173): constants.py, state.py (items, state, lines, preview), table.py (screen
and CSV), actions.py (Finalize & export, Mark as paid) and backfill.py (build_registers).
Everything public is importable from here.
"""

from apps.payroll.services.register.actions import (
    finalize,
    mark_paid,
)
from apps.payroll.services.register.backfill import (
    build_registers,
    unregistered_periods,
)
from apps.payroll.services.register.constants import (
    ADJUSTMENT,
    BACKFILL_ACTOR,
    LATE_WEEK,
    OPEN,
    READY,
    Line,
)
from apps.payroll.services.register.state import (
    Items,
    PeriodState,
    Preview,
    build_lines,
    ended_periods,
    period_items,
    period_state,
    preview,
)
from apps.payroll.services.register.table import (
    PERIOD_COLUMNS,
    REGISTER_COLUMNS,
    Row,
    carry_from_text,
    file_stem,
    register_csv,
    table,
)

__all__ = [
    "OPEN",
    "READY",
    "BACKFILL_ACTOR",
    "LATE_WEEK",
    "ADJUSTMENT",
    "Line",
    "Items",
    "period_items",
    "PeriodState",
    "period_state",
    "ended_periods",
    "build_lines",
    "Preview",
    "preview",
    "carry_from_text",
    "Row",
    "table",
    "register_csv",
    "file_stem",
    "REGISTER_COLUMNS",
    "PERIOD_COLUMNS",
    "finalize",
    "mark_paid",
    "unregistered_periods",
    "build_registers",
]
