"""Pay period registers (Change 8, D-132–D-137): one table per 2-week pay period, one line per
employee, with carry-forward columns.

While a period's register is not finalized its status is worked out live: OPEN until every
person who must be approved is approved (Change 9, D-142), then READY. "Finalize & export"
saves it once — one batch, frozen lines — and "Mark as paid" closes it. Every number
comes from the PayrollWeek and PayrollAdjustment records (their split from hours.py); nothing
is worked out a second way, and timesheet rows or reasons never appear here (D-12, D-122).
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from audit.models import AuditLog
from audit.services.log import record
from directory.models import Employee
from payroll.models import (
    CATEGORIES,
    PayrollAdjustment,
    PayrollRegister,
    PayrollRegisterLine,
    PayrollWeek,
)
from payroll.services.adjustments import PERIOD, closed_periods, next_open_period
from payroll.services.export import hours, next_batch, safe_cell
from timesheets.models import ChangeRequest, PeriodApproval, Timesheet
from timesheets.services.approvals import must_be_approved, pending_by_manager
from timesheets.services.calendar import (
    approval_deadline_for,
    current_period,
    period_end_for,
    period_ended,
)

OPEN, READY = "OPEN", "READY"  # worked out live; FINALIZED and PAID are saved
BACKFILL_ACTOR = "build_registers"
LATE_WEEK, ADJUSTMENT = "LATE_WEEK", "ADJUSTMENT"
Line = PayrollRegisterLine.Status


# --- what belongs to a period ----------------------------------------------------------------


def _target(item, closed):
    """The pay period a CURRENT record is paid in: its own one, or — when that one is closed —
    the first open period after it (late weeks, stranded adjustments; D-136)."""
    return next_open_period(item.period_start, closed)


@dataclass
class Items:
    """The CURRENT records a period's register would pay."""

    weeks: list = field(default_factory=list)  # the period's own week records
    late: list = field(default_factory=list)  # weeks approved after their register (D-136)
    adjustments: list = field(default_factory=list)  # carried here (D-121, D-136)

    @property
    def total(self):
        return sum(r.total_minutes for r in self.weeks + self.late + self.adjustments)


def period_items(period_start, closed=None):
    closed = closed_periods() if closed is None else closed
    items = Items()
    if period_start in closed:
        return items
    weeks = PayrollWeek.objects.filter(
        status=PayrollWeek.Status.CURRENT, period_start__lte=period_start
    ).order_by("employee_code", "week_start")
    for w in weeks:
        if w.period_start == period_start:
            items.weeks.append(w)
        elif _target(w, closed) == period_start:
            items.late.append(w)
    adjustments = PayrollAdjustment.objects.filter(
        status=PayrollAdjustment.Status.CURRENT, period_start__lte=period_start
    ).order_by("employee_code", "week_start", "new_version")
    items.adjustments = [a for a in adjustments if _target(a, closed) == period_start]
    return items


# --- the period's state (OPEN / READY / FINALIZED / PAID) -------------------------------------


@dataclass
class PeriodState:
    period_start: object
    status: str
    register: PayrollRegister | None
    required: int
    approved: int
    deadline: object
    deadline_passed: bool
    open_requests: int = 0
    missing_records: int = 0
    pay_total: int = 0
    ready_reason: str = ""
    ended: bool = True

    @property
    def period_end(self):
        return period_end_for(self.period_start)

    @property
    def finalized(self):
        return self.register is not None

    @property
    def waiting_for(self):
        """Why the register isn't READY yet, in words (empty once it is)."""
        if self.status != OPEN:
            return []
        if not self.ended:
            return ["This pay period hasn't ended yet."]
        reasons = []
        if self.missing_records:
            reasons.append(
                f"{self.missing_records} approved week(s) have no payroll record yet — ask an "
                "admin to run sync_payroll."
            )
        if self.approved < self.required:
            reasons.append(
                f"{self.required - self.approved} of {self.required} people are not approved yet."
            )
        if self.open_requests:
            reasons.append(f"{self.open_requests} open change request(s) on this period.")
        return reasons


def _missing_records(period_start, people):
    """Approved weeks of the period without a live payroll record (sync needed, D-65)."""
    approved = set(
        Timesheet.objects.filter(
            employee__in=people,
            week_start__in=(period_start, period_start + timedelta(weeks=1)),
            status=Timesheet.Status.APPROVED,
        ).values_list("employee__employee_code", "week_start")
    )
    live = set(
        PayrollWeek.objects.filter(period_start=period_start)
        .exclude(status=PayrollWeek.Status.SUPERSEDED)
        .values_list("employee_code", "week_start")
    )
    return len(approved - live)


def period_state(period_start, now, closed=None):
    """The register's status right now (D-132, D-142). READY needs the period to have ended,
    every person who must be approved APPROVED, no open change request on its weeks, and
    payroll in sync. The approval deadline is only a reminder (Overdue); it never makes a
    register READY."""
    deadline = approval_deadline_for(period_start)
    register = PayrollRegister.objects.filter(period_start=period_start).first()
    if register is not None:
        return PeriodState(
            period_start,
            register.status,
            register,
            register.required_count,
            register.approved_count,
            deadline,
            True,
            pay_total=sum(line.pay_total_minutes for line in register.lines.all()),
            ready_reason=register.ready_reason,
        )
    people = must_be_approved(Employee.objects.select_related("team"), period_start)
    approved = PeriodApproval.objects.filter(
        employee__in=people, period_start=period_start, status=PeriodApproval.Status.APPROVED
    ).count()
    open_requests = ChangeRequest.objects.filter(
        timesheet__employee__in=people,
        timesheet__week_start__in=(period_start, period_start + timedelta(weeks=1)),
        status=ChangeRequest.Status.OPEN,
    ).count()
    state = PeriodState(
        period_start,
        OPEN,
        None,
        len(people),
        approved,
        deadline,
        now >= deadline,
        open_requests=open_requests,
        missing_records=_missing_records(period_start, people),
        pay_total=period_items(period_start, closed).total,
        ended=period_ended(period_start, now),
    )
    everyone = approved == len(people) and not open_requests
    if state.ended and not state.missing_records and everyone:
        state.status = READY
        state.ready_reason = PayrollRegister.Ready.ALL_APPROVED
    return state


def ended_periods(now):
    """Every ended pay period from the oldest one payroll knows about, newest first."""
    last = current_period(now) - PERIOD
    known = [
        *PayrollWeek.objects.values_list("period_start", flat=True),
        *PayrollAdjustment.objects.values_list("period_start", flat=True),
        *PayrollRegister.objects.values_list("period_start", flat=True),
        *PeriodApproval.objects.values_list("period_start", flat=True),
    ]
    first = min([p for p in known if p <= last], default=last)
    periods = []
    while last >= first:
        periods.append(last)
        last -= PERIOD
    return periods


# --- the register's lines -------------------------------------------------------------------


def _line_for_record(r, status):
    """An unsaved line for the record's employee, plus what it pays (week_records,
    adjustments)."""
    line = PayrollRegisterLine(
        employee_code=r.employee_code,
        employee_name=r.employee_name,
        department=r.department,
        team=r.team,
        status=status,
    )
    line.week_records, line.adjustments = [], []
    return line


def _approval(line, r):
    line.approved_by_code, line.approved_by_name = r.approved_by_code, r.approved_by_name
    line.approved_at = r.approved_at


def _carry(line, r, kind):
    for c in CATEGORIES:
        name = f"carry_{c}_minutes"
        setattr(line, name, getattr(line, name) + getattr(r, f"{c}_minutes"))
    line.carry_total_minutes += r.total_minutes
    line.carry_from = [
        *line.carry_from,
        {"week": r.week_start.isoformat(), "kind": kind, "total_minutes": r.total_minutes},
    ]


def _week(line, r, period_start):
    number = 1 if r.week_start == period_start else 2
    for c in CATEGORIES:
        name = f"week{number}_{c}_minutes"
        setattr(line, name, getattr(line, name) + getattr(r, f"{c}_minutes"))


def build_lines(period_start, items):
    """The register's lines (unsaved), only from the records it pays (D-134, D-142): one per
    person with approved weeks in the period, and one for anyone with only something carried
    forward. A register is finalized only when everyone is approved, so nobody gets a 0.00
    line any more ("Missed – not submitted" / "Waiting for manager approval" stay only on
    registers saved before Change 9)."""
    lines = {}
    for r in items.weeks:
        line = lines.get(r.employee_code)
        if line is None:
            line = lines[r.employee_code] = _line_for_record(r, Line.APPROVED)
        _week(line, r, period_start)
        _approval(line, r)
        line.week_records.append(r)
    for kind, records in ((LATE_WEEK, items.late), (ADJUSTMENT, items.adjustments)):
        for r in records:
            line = lines.get(r.employee_code)
            if line is None:
                line = lines[r.employee_code] = _line_for_record(r, Line.CARRY_ONLY)
            _carry(line, r, kind)
            if not line.approved_at:
                _approval(line, r)
            (line.adjustments if kind == ADJUSTMENT else line.week_records).append(r)
    return sorted(lines.values(), key=lambda line: (line.employee_name, line.employee_code))


@dataclass
class Preview:
    state: PeriodState
    lines: list  # empty while OPEN: no hours before everyone is approved (D-142)
    pending: object = None  # approvals.PendingReport while OPEN


def preview(period_start, now):
    """The register as it stands: the saved lines once finalized, the lines it would save once
    READY, and while OPEN only who is still pending (D-142)."""
    closed = closed_periods()
    state = period_state(period_start, now, closed)
    if state.register is not None:
        lines = list(state.register.lines.order_by("employee_name", "employee_code"))
        return Preview(state, lines)
    if state.status == READY:
        return Preview(state, build_lines(period_start, period_items(period_start, closed)))
    return Preview(state, [], pending_by_manager(period_start, now))


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


# --- Finalize & export, Mark as paid ----------------------------------------------------------


def _actor_fields(actor, system_actor):
    if actor is not None:
        return actor.employee_code, f"{actor.first_name} {actor.last_name}"
    return "", system_actor


def finalize(period_start, *, actor=None, system_actor="", now):
    """Finalize & export (D-135): only when READY. In one payroll transaction the lines are
    saved, and every week record and adjustment they pay becomes EXPORTED in one new batch.
    Returns the register."""
    state = period_state(period_start, now)
    if state.finalized:
        raise ValidationError("This pay period's register is already finalized.")
    if state.status != READY:
        raise ValidationError(state.waiting_for)
    code, name = _actor_fields(actor, system_actor)
    with transaction.atomic(using="payroll"):
        if PayrollRegister.objects.filter(period_start=period_start).exists():
            raise ValidationError("This pay period's register is already finalized.")
        items = period_items(period_start)
        lines = build_lines(period_start, items)
        batch = next_batch()
        for r in items.weeks + items.late + items.adjustments:
            r.status = r.Status.EXPORTED
            r.export_batch = batch
            r.exported_at = now
            r.save()
        register = PayrollRegister.objects.create(
            period_start=period_start,
            period_end=period_end_for(period_start),
            export_batch=batch,
            ready_reason=state.ready_reason,
            required_count=state.required,
            approved_count=state.approved,
            finalized_at=now,
            finalized_by_code=code,
            finalized_by_name=name,
        )
        _save_lines(register, lines)
    record(
        AuditLog.Action.EXPORT,
        "PayrollRegister",
        period_start.isoformat(),
        actor=actor,
        system_actor=system_actor,
        after={
            "period_start": period_start,
            "batch": batch,
            "lines": len(lines),
            "records": len(items.weeks) + len(items.late),
            "late_weeks": len(items.late),
            "adjustments": len(items.adjustments),
            "total_minutes": items.total,
        },
        at=now,
    )
    return register


def _save_lines(register, lines):
    for line in lines:
        line.register = register
        line.week_record_ids = [r.pk for r in line.week_records]
        line.adjustment_ids = [a.pk for a in line.adjustments]
    PayrollRegisterLine.objects.bulk_create(lines)


def mark_paid(period_start, *, actor=None, system_actor="", at):
    """Mark as paid (D-135): the register and the records of its batch become PAID, once.
    Returns (week records, adjustments) paid now, or None if it was already paid."""
    with transaction.atomic(using="payroll"):
        register = PayrollRegister.objects.get(period_start=period_start)
        if register.status == PayrollRegister.Status.PAID:
            return None
        weeks = list(
            PayrollWeek.objects.filter(
                export_batch__in=register.batches, status=PayrollWeek.Status.EXPORTED
            )
        )
        adjustments = list(
            PayrollAdjustment.objects.filter(
                export_batch__in=register.batches, status=PayrollAdjustment.Status.EXPORTED
            )
        )
        for r in weeks + adjustments:
            r.status = r.Status.PAID
            r.paid_at = at
            r.save()
        register.status = PayrollRegister.Status.PAID
        register.paid_at = at
        register.save()
    record(
        AuditLog.Action.PAY,
        "PayrollRegister",
        period_start.isoformat(),
        actor=actor,
        system_actor=system_actor,
        after={
            "period_start": period_start,
            "batch": register.export_batch,
            "records": len(weeks),
            "adjustments": len(adjustments),
        },
        at=at,
    )
    return len(weeks), len(adjustments)


# --- registers for periods exported before registers existed (D-137) --------------------------


def unregistered_periods():
    """Periods with an export batch but no register: data from before Change 8."""
    exported = {
        *PayrollWeek.objects.exclude(export_batch="").values_list("period_start", flat=True),
        *PayrollAdjustment.objects.exclude(export_batch="").values_list("period_start", flat=True),
    }
    return sorted(exported - set(PayrollRegister.objects.values_list("period_start", flat=True)))


def build_registers(*, system_actor=BACKFILL_ACTOR, at):
    """A FINALIZED register (PAID when its batches were paid) for every period that was
    exported before registers existed, built from exactly what was exported. Idempotent.
    Returns the registers created."""
    created = []
    for period_start in unregistered_periods():
        weeks = list(
            PayrollWeek.objects.filter(period_start=period_start)
            .exclude(export_batch="")
            .order_by("employee_code", "week_start", "version")
        )
        adjustments = list(
            PayrollAdjustment.objects.filter(period_start=period_start)
            .exclude(export_batch="")
            .order_by("employee_code", "week_start", "new_version")
        )
        lines = build_lines(period_start, Items(weeks=weeks, adjustments=adjustments))
        exported = weeks + adjustments
        people = must_be_approved(Employee.objects.select_related("team"), period_start)
        with transaction.atomic(using="payroll"):
            if PayrollRegister.objects.filter(period_start=period_start).exists():
                continue
            register = PayrollRegister.objects.create(
                period_start=period_start,
                period_end=period_end_for(period_start),
                export_batch="+".join(sorted({r.export_batch for r in exported})),
                ready_reason=PayrollRegister.Ready.BACKFILL,
                required_count=len(people),
                approved_count=PeriodApproval.objects.filter(
                    employee__in=people,
                    period_start=period_start,
                    status=PeriodApproval.Status.APPROVED,
                ).count(),
                finalized_at=min(r.exported_at for r in exported),
                finalized_by_name=system_actor,
            )
            _save_lines(register, lines)
            paid = [r.paid_at for r in exported if r.paid_at]
            if paid and not any(r.status == "EXPORTED" for r in exported):
                register.status = PayrollRegister.Status.PAID
                register.paid_at = max(paid)
                register.save()
        record(
            AuditLog.Action.PUBLISH,
            "PayrollRegister",
            period_start.isoformat(),
            system_actor=system_actor,
            after={
                "period_start": period_start,
                "batch": register.export_batch,
                "lines": len(lines),
                "status": register.status,
            },
            at=at,
        )
        created.append(register)
    return created
