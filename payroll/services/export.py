"""Export batches, the CSV file, Mark as paid, totals and corrections (FR-11, B.9 #14)."""

import csv
import io
from collections import defaultdict
from dataclasses import dataclass

from django.db import transaction

from audit.models import AuditLog
from audit.services.log import record
from payroll.models import PayrollWeek

BATCH_PREFIX = "EXP-"
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")
CSV_COLUMNS = (
    ("batch", lambda r: r.export_batch),
    ("employee_code", lambda r: r.employee_code),
    ("employee_name", lambda r: r.employee_name),
    ("department", lambda r: r.department),
    ("team", lambda r: r.team),
    ("period_start", lambda r: r.period_start.isoformat()),
    ("week_start", lambda r: r.week_start.isoformat()),
    ("regular_hours", lambda r: hours(r.regular_minutes)),
    ("overtime_hours", lambda r: hours(r.overtime_minutes)),
    ("pto_hours", lambda r: hours(r.pto_minutes)),
    ("sick_hours", lambda r: hours(r.sick_minutes)),
    ("holiday_hours", lambda r: hours(r.holiday_minutes)),
    ("total_hours", lambda r: hours(r.total_minutes)),
    ("expected_hours", lambda r: hours(r.expected_weekly_minutes)),
    ("approved_by", lambda r: r.approved_by_name),
    ("approved_at", lambda r: r.approved_at.isoformat()),
    ("version", lambda r: r.version),
    ("status", lambda r: r.status),
)


def hours(minutes):
    """Minutes as hours with 2 decimals: 450 → "7.50" (D-64)."""
    return f"{minutes / 60:.2f}"


def safe_cell(value):
    """Spreadsheet-safe text: a cell starting with = + - @ (or tab/CR) gets a leading ' (D-68)."""
    text = str(value)
    return f"'{text}" if text.startswith(FORMULA_STARTS) else text


def next_batch():
    used = PayrollWeek.objects.exclude(export_batch="").values_list("export_batch", flat=True)
    numbers = [int(b.removeprefix(BATCH_PREFIX)) for b in set(used) if b.startswith(BATCH_PREFIX)]
    return f"{BATCH_PREFIX}{max(numbers, default=0) + 1:04d}"


def export_period(period_start, *, actor=None, system_actor="", at):
    """Every CURRENT record of the period becomes EXPORTED in one new batch (D-68).

    Returns the batch number, or None if there was nothing to export.
    """
    with transaction.atomic(using="payroll"):
        records = list(
            PayrollWeek.objects.filter(
                period_start=period_start, status=PayrollWeek.Status.CURRENT
            ).order_by("employee_code", "week_start")
        )
        if not records:
            return None
        batch = next_batch()
        for r in records:
            r.status = PayrollWeek.Status.EXPORTED
            r.export_batch = batch
            r.exported_at = at
            r.save()
    record(
        AuditLog.Action.EXPORT,
        "PayrollBatch",
        batch,
        actor=actor,
        system_actor=system_actor,
        after={
            "period_start": period_start,
            "records": len(records),
            "total_minutes": sum(r.total_minutes for r in records),
        },
        at=at,
    )
    return batch


def batch_csv(batch):
    """The batch as CSV text, every cell spreadsheet-safe (D-68)."""
    records = PayrollWeek.objects.filter(export_batch=batch).order_by("employee_code", "week_start")
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([name for name, _ in CSV_COLUMNS])
    for r in records:
        writer.writerow([safe_cell(value(r)) for _, value in CSV_COLUMNS])
    return out.getvalue()


def mark_paid(batch, *, actor=None, system_actor="", at):
    """EXPORTED records of the batch become PAID; returns how many (D-69)."""
    with transaction.atomic(using="payroll"):
        records = list(
            PayrollWeek.objects.filter(export_batch=batch, status=PayrollWeek.Status.EXPORTED)
        )
        for r in records:
            r.status = PayrollWeek.Status.PAID
            r.paid_at = at
            r.save()
    if records:
        record(
            AuditLog.Action.PAY,
            "PayrollBatch",
            batch,
            actor=actor,
            system_actor=system_actor,
            after={"records": len(records)},
            at=at,
        )
    return len(records)


@dataclass
class EmployeeTotals:
    employee_code: str
    employee_name: str
    department: str
    team: str
    regular: int = 0
    overtime: int = 0
    pto: int = 0
    sick: int = 0
    holiday: int = 0
    total: int = 0


def employee_totals(records):
    """Per-employee sums of the given records, by name."""
    totals = {}
    for r in records:
        t = totals.setdefault(
            r.employee_code, EmployeeTotals(r.employee_code, r.employee_name, r.department, r.team)
        )
        t.regular += r.regular_minutes
        t.overtime += r.overtime_minutes
        t.pto += r.pto_minutes
        t.sick += r.sick_minutes
        t.holiday += r.holiday_minutes
        t.total += r.total_minutes
    return sorted(totals.values(), key=lambda t: t.employee_name)


def batches_for(period_start):
    """[(batch, exported_at, records, still EXPORTED, PAID)] for the period."""
    found = defaultdict(lambda: {"exported_at": None, "records": 0, "exported": 0, "paid": 0})
    for r in PayrollWeek.objects.filter(period_start=period_start).exclude(export_batch=""):
        info = found[r.export_batch]
        info["exported_at"] = info["exported_at"] or r.exported_at
        info["records"] += 1
        info["exported"] += r.status == PayrollWeek.Status.EXPORTED
        info["paid"] += r.status == PayrollWeek.Status.PAID
    return [{"batch": b, **found[b]} for b in sorted(found)]


@dataclass
class Correction:
    old: PayrollWeek
    new: PayrollWeek | None

    @property
    def difference(self):
        return (self.new.total_minutes if self.new else 0) - self.old.total_minutes

    @property
    def difference_text(self):
        """Signed hours, e.g. "+1.00", "−0.50", "0.00"."""
        sign = "+" if self.difference > 0 else "−" if self.difference < 0 else ""
        return f"{sign}{hours(abs(self.difference))}"


def corrections():
    """Weeks superseded after they were exported or paid, with their replacement (D-70)."""
    old_records = PayrollWeek.objects.filter(
        status=PayrollWeek.Status.SUPERSEDED, exported_at__isnull=False
    ).order_by("-superseded_at")
    live = {
        (r.employee_code, r.week_start): r
        for r in PayrollWeek.objects.exclude(status=PayrollWeek.Status.SUPERSEDED)
    }
    return [Correction(r, live.get((r.employee_code, r.week_start))) for r in old_records]
