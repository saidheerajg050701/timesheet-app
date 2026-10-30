"""Export batches, the CSV file, Mark as paid, totals and corrections (FR-11, B.9 #14)."""

import csv
import io
from collections import defaultdict
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q

from apps.audit.models import AuditLog
from apps.audit.services.log import record
from apps.payroll.models import PayrollAdjustment, PayrollRegister, PayrollWeek
from apps.payroll.services.adjustments import closed_periods, next_open_period

BATCH_PREFIX = "EXP-"
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def is_adjustment(r):
    return isinstance(r, PayrollAdjustment)


# (column, value, numeric). Numeric columns are hours the app computes — written as plain
# numbers (adjustments may be negative, "-1.50"); every text column goes through safe_cell
# (D-68, D-123). WEEK rows and ADJUSTMENT rows share the columns.
CSV_COLUMNS = (
    ("batch", lambda r: r.export_batch, False),
    ("employee_code", lambda r: r.employee_code, False),
    ("row_type", lambda r: "ADJUSTMENT" if is_adjustment(r) else "WEEK", False),
    ("employee_name", lambda r: r.employee_name, False),
    ("department", lambda r: r.department, False),
    ("team", lambda r: r.team, False),
    ("period_start", lambda r: r.period_start.isoformat(), False),
    ("week_start", lambda r: "" if is_adjustment(r) else r.week_start.isoformat(), False),
    ("original_week", lambda r: r.week_start.isoformat() if is_adjustment(r) else "", False),
    ("regular_hours", lambda r: hours(r.regular_minutes), True),
    ("overtime_hours", lambda r: hours(r.overtime_minutes), True),
    ("pto_hours", lambda r: hours(r.pto_minutes), True),
    ("sick_hours", lambda r: hours(r.sick_minutes), True),
    ("holiday_hours", lambda r: hours(r.holiday_minutes), True),
    ("total_hours", lambda r: hours(r.total_minutes), True),
    (
        "expected_hours",
        lambda r: "" if is_adjustment(r) else hours(r.expected_weekly_minutes),
        True,
    ),
    ("approved_by", lambda r: r.approved_by_name, False),
    ("approved_at", lambda r: r.approved_at.isoformat(), False),
    (
        "version",
        lambda r: f"{r.old_version}→{r.new_version}" if is_adjustment(r) else r.version,
        False,
    ),
    ("status", lambda r: r.status, False),
)


def hours(minutes):
    """Minutes as hours with 2 decimals: 450 → "7.50" (D-64)."""
    return f"{minutes / 60:.2f}"


def safe_cell(value):
    """Spreadsheet-safe text: a cell starting with = + - @ (or tab/CR) gets a leading ' (D-68)."""
    text = str(value)
    return f"'{text}" if text.startswith(FORMULA_STARTS) else text


def next_batch():
    """The next free EXP- number, also past batches a register holds with nothing in it."""
    registers = PayrollRegister.objects.values_list("export_batch", flat=True)
    used = {
        *PayrollWeek.objects.exclude(export_batch="").values_list("export_batch", flat=True),
        *PayrollAdjustment.objects.exclude(export_batch="").values_list("export_batch", flat=True),
        *(batch for joined in registers for batch in joined.split("+")),
    }
    numbers = [int(b.removeprefix(BATCH_PREFIX)) for b in set(used) if b.startswith(BATCH_PREFIX)]
    return f"{BATCH_PREFIX}{max(numbers, default=0) + 1:04d}"


def counted(adjustments):
    """{"adjustments": n} for audit rows, only when the batch has any (D-125)."""
    return {"adjustments": len(adjustments)} if adjustments else {}


def exportable(period_start):
    """(CURRENT week records, CURRENT adjustments) of the period: its next pay run (D-123)."""
    weeks = PayrollWeek.objects.filter(
        period_start=period_start, status=PayrollWeek.Status.CURRENT
    ).order_by("employee_code", "week_start")
    adjustments = PayrollAdjustment.objects.filter(
        period_start=period_start, status=PayrollAdjustment.Status.CURRENT
    ).order_by("employee_code", "week_start", "new_version")
    return list(weeks), list(adjustments)


def export_period(period_start, *, actor=None, system_actor="", at):
    """Every CURRENT week record and adjustment of the period becomes EXPORTED in one new
    batch (D-68, D-123). SETTLED weeks are never exported (D-118).

    Before Change 8 this was the Export CSV button. Now "Finalize & export" (register.finalize)
    is the only action that creates a batch (D-135); no page or command calls this any more —
    it stays to build data "as it was before registers" for tests of build_registers.

    Returns the batch number, or None if there was nothing to export.
    """
    with transaction.atomic(using="payroll"):
        records, adjustments = exportable(period_start)
        if not records and not adjustments:
            return None
        batch = next_batch()
        for r in records + adjustments:
            r.status = r.Status.EXPORTED
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
            **counted(adjustments),
            "total_minutes": sum(r.total_minutes for r in records + adjustments),
        },
        at=at,
    )
    return batch


def batch_rows(*batches):
    """The batches' week records and adjustments: per employee, weeks first (D-123)."""
    weeks = PayrollWeek.objects.filter(export_batch__in=batches)
    adjustments = PayrollAdjustment.objects.filter(export_batch__in=batches)
    return sorted(
        [*weeks, *adjustments],
        key=lambda r: (r.employee_code, is_adjustment(r), r.week_start, str(r.pk)),
    )


def batch_csv(batch):
    """The batch as CSV text; every text cell spreadsheet-safe (D-68, D-123)."""
    return batches_csv([batch])


def batches_csv(batches):
    """The detailed CSV for one or more batches (a register's, D-135): WEEK / ADJUSTMENT rows."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([name for name, _, _ in CSV_COLUMNS])
    for r in batch_rows(*batches):
        writer.writerow(
            [value(r) if numeric else safe_cell(value(r)) for _, value, numeric in CSV_COLUMNS]
        )
    return out.getvalue()


def mark_paid(batch, *, actor=None, system_actor="", at):
    """EXPORTED week records and adjustments of the batch become PAID (D-69, D-123).
    Returns how many week records (mark_paid_counts also gives the adjustments)."""
    return mark_paid_counts(batch, actor=actor, system_actor=system_actor, at=at)[0]


def mark_paid_counts(batch, *, actor=None, system_actor="", at):
    """(week records, adjustments) of the batch that became PAID now."""
    with transaction.atomic(using="payroll"):
        records = list(
            PayrollWeek.objects.filter(export_batch=batch, status=PayrollWeek.Status.EXPORTED)
        )
        adjustments = list(
            PayrollAdjustment.objects.filter(
                export_batch=batch, status=PayrollAdjustment.Status.EXPORTED
            )
        )
        for r in records + adjustments:
            r.status = r.Status.PAID
            r.paid_at = at
            r.save()
    if records or adjustments:
        record(
            AuditLog.Action.PAY,
            "PayrollBatch",
            batch,
            actor=actor,
            system_actor=system_actor,
            after={"records": len(records), **counted(adjustments)},
            at=at,
        )
    return len(records), len(adjustments)


@dataclass
class Correction:
    """One change to a week that had been exported: old version → new version (or still
    waiting for re-approval), with the adjustment that pays the difference (D-124)."""

    old: PayrollWeek
    new: PayrollWeek | None
    adjustment: PayrollAdjustment | None = None
    register_period: object = None  # the pay period whose register pays the adjustment (D-138)
    register: PayrollRegister | None = None  # that register, once finalized

    @property
    def difference(self):
        return (self.new.total_minutes if self.new else 0) - self.old.total_minutes

    @property
    def difference_text(self):
        """Signed hours, e.g. "+1.00", "−0.50", "0.00"."""
        sign = "+" if self.difference > 0 else "−" if self.difference < 0 else ""
        return f"{sign}{hours(abs(self.difference))}"

    @property
    def adjustment_status(self):
        """Scheduled / Exported in EXP-0002 / Paid (D-124)."""
        a = self.adjustment
        if a is None:
            return ""
        if a.status == PayrollAdjustment.Status.PAID:
            return f"Paid ({a.export_batch})"
        if a.status == PayrollAdjustment.Status.EXPORTED:
            return f"Exported in {a.export_batch}"
        return "Scheduled"


def _registers_for(rows):
    """Where each adjustment is paid: the register holding its batch, or — still scheduled —
    the first pay period from its own one whose register isn't finalized (D-136, D-138)."""
    registers = list(PayrollRegister.objects.all())
    by_batch = {batch: r for r in registers for batch in r.batches}
    by_period = {r.period_start: r for r in registers}
    closed = closed_periods()
    for row in rows:
        a = row.adjustment
        if a is None:
            continue
        register = by_batch.get(a.export_batch) if a.export_batch else None
        row.register_period = (
            register.period_start if register else (next_open_period(a.period_start, closed))
        )
        row.register = register or by_period.get(row.register_period)


def corrections():
    """Every version change of a week that had been exported or settled (D-124, replaces D-70)."""
    superseded = PayrollWeek.objects.filter(status=PayrollWeek.Status.SUPERSEDED).filter(
        Q(exported_at__isnull=False) | Q(settled_at__isnull=False)
    )
    by_week = defaultdict(list)
    for r in PayrollWeek.objects.filter(
        employee_code__in={r.employee_code for r in superseded}
    ).order_by("version"):
        by_week[(r.employee_code, r.week_start)].append(r)
    adjustments = {
        (a.employee_code, a.week_start, a.new_version): a for a in PayrollAdjustment.objects.all()
    }
    rows = []
    for old in superseded:
        later = [r for r in by_week[(old.employee_code, old.week_start)] if r.version > old.version]
        new = later[0] if later else None
        key = (old.employee_code, old.week_start, new.version if new else None)
        rows.append(Correction(old, new, adjustments.get(key)))
    _registers_for(rows)
    rows.sort(key=lambda c: (c.old.employee_code, c.old.week_start, c.old.version))
    return sorted(rows, key=lambda c: c.old.superseded_at, reverse=True)  # newest first, stable
