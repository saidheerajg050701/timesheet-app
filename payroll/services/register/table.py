"""The register as a table on screen and in the CSVs (D-135, D-138)."""

import csv
import io
from dataclasses import dataclass

from payroll.models import (
    CATEGORIES,
    PayrollRegisterLine,
)
from payroll.services.export import hours, safe_cell
from payroll.services.register.constants import (
    ADJUSTMENT,
    LATE_WEEK,
)

# --- the table on screen and in the CSV -------------------------------------------------------


def carry_from_text(items):
    """ "2026-09-13 correction +1.00; 2026-09-27 late approval +40.00" """
    words = {ADJUSTMENT: "correction", LATE_WEEK: "late approval"}
    parts = []
    for item in items:
        minutes = item["total_minutes"]
        sign = "+" if minutes > 0 else "−" if minutes < 0 else ""
        parts.append(f"{item['week']} {words[item['kind']]} {sign}{hours(abs(minutes))}")
    return "; ".join(parts)


@dataclass
class Row:
    line: PayrollRegisterLine
    week1: list
    week2: list
    period: list  # five categories, then the period total
    carry: list  # five categories, then the carry total
    pay_total: int


def table(lines):
    """(rows, totals) for the register table; totals has the same lists, summed (D-134)."""
    rows = []
    for line in lines:
        week1 = [getattr(line, f"week1_{c}_minutes") for c in CATEGORIES]
        week2 = [getattr(line, f"week2_{c}_minutes") for c in CATEGORIES]
        period = [a + b for a, b in zip(week1, week2, strict=True)]
        carry = [getattr(line, f"carry_{c}_minutes") for c in CATEGORIES]
        rows.append(
            Row(
                line,
                week1,
                week2,
                [*period, sum(period)],
                [*carry, line.carry_total_minutes],
                sum(period) + line.carry_total_minutes,
            )
        )

    def summed(name):
        values = [getattr(r, name) for r in rows]
        return [sum(column) for column in zip(*values, strict=True)] if values else []

    totals = {
        "week1": summed("week1") or [0] * 5,
        "week2": summed("week2") or [0] * 5,
        "period": summed("period") or [0] * 6,
        "carry": summed("carry") or [0] * 6,
        "pay_total": sum(r.pay_total for r in rows),
    }
    return rows, totals


REGISTER_COLUMNS = (
    "employee_code",
    "employee_name",
    "department",
    "team",
    "approved_by",
    "approved_at",
    "line_status",
    *(f"week{n}_{c}_hours" for n in (1, 2) for c in CATEGORIES),
    *(f"period_{c}_hours" for c in CATEGORIES),
    "period_total_hours",
    *(f"carry_{c}_hours" for c in CATEGORIES),
    "carry_total_hours",
    "carry_from",
    "pay_total_hours",
)
PERIOD_COLUMNS = ("period_start", "period_end", "batch")


def _csv_row(row):
    line = row.line
    text = [
        line.employee_code,
        line.employee_name,
        line.department,
        line.team,
        line.approved_by_name,
        line.approved_at.isoformat() if line.approved_at else "",
        line.get_status_display(),
    ]
    numbers = [hours(m) for m in [*row.week1, *row.week2, *row.period, *row.carry[:5]]]
    return (
        [safe_cell(v) for v in text]
        + numbers
        + [
            hours(line.carry_total_minutes),
            safe_cell(carry_from_text(line.carry_from)),
            hours(row.pay_total),
        ]
    )


def register_csv(registers, *, with_period=False):
    """Register CSV text: one row per line (D-135). Hours are numbers the app computes;
    every text cell is spreadsheet-safe (D-68). `with_period` adds period and batch columns."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([*(PERIOD_COLUMNS if with_period else ()), *REGISTER_COLUMNS])
    for register in registers:
        lines = register.lines.order_by("employee_name", "employee_code")
        prefix = [
            register.period_start.isoformat(),
            register.period_end.isoformat(),
            safe_cell(register.export_batch),
        ]
        for row in table(lines)[0]:
            writer.writerow([*(prefix if with_period else ()), *_csv_row(row)])
    return out.getvalue()


def file_stem(register):
    """ "2026-10-11_to_2026-10-24_EXP-0007" (D-135)."""
    return f"{register.period_start}_to_{register.period_end}_{register.export_batch}"
