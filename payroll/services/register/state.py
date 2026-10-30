"""What belongs to a pay period, its live state (OPEN / READY / FINALIZED / PAID), its lines
and the preview (D-132–D-136, D-142)."""

from dataclasses import dataclass, field
from datetime import timedelta

from directory.models import Employee
from payroll.models import (
    CATEGORIES,
    PayrollAdjustment,
    PayrollRegister,
    PayrollRegisterLine,
    PayrollWeek,
)
from payroll.services.adjustments import PERIOD, closed_periods, next_open_period
from payroll.services.register.constants import (
    ADJUSTMENT,
    LATE_WEEK,
    OPEN,
    READY,
    Line,
)
from timesheets.models import ChangeRequest, PeriodApproval, Timesheet
from timesheets.services.approvals import must_be_approved
from timesheets.services.calendar import (
    approval_deadline_for,
    current_period,
    period_end_for,
    period_ended,
)
from timesheets.services.pending import pending_by_manager

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
