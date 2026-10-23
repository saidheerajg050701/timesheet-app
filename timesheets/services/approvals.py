"""The only code that moves a week to or from APPROVED (D-10, B.9 #10).

Biweekly approval (FR-7, D-54–D-63): the approvals page rows, approve, reject, bulk approve,
plus the Phase 6 reset/unlock used by change requests. Every change here happens in one
transaction with its PeriodApproval.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from audit.models import AuditLog
from audit.services.log import record
from directory.models import Employee
from directory.services.permissions import can_approve
from timesheets.models import ChangeRequest, PeriodApproval, Timesheet
from timesheets.services.calendar import (
    OUTSIDE_EMPLOYMENT,
    WeekState,
    company_tz,
    employed_on,
    pay_period_for,
    reopen_until_for,
    week_state,
)
from timesheets.services.summary import WeekSummary, summarize


def supersede_payroll_week(timesheet, *, actor, at):
    """Payroll hook (D-53): called for every week that leaves APPROVED.

    Phase 8 replaces this body with payroll/services/publish.py → supersede_week(...), which
    marks the week's CURRENT PayrollWeek as SUPERSEDED (D-15). Until then there are no
    payroll records, so there is nothing to do.
    """
    return None


def reset_approval(employee, period_start, *, actor, change_request=None, at):
    """An approved period goes back to PENDING; its approved weeks back to SUBMITTED.

    Returns the weeks that left APPROVED. Safe to call when nothing is approved.
    """
    with transaction.atomic():
        approval = (
            PeriodApproval.objects.select_for_update()
            .filter(employee=employee, period_start=period_start)
            .first()
        )
        weeks = list(
            Timesheet.objects.select_for_update().filter(
                employee=employee,
                week_start__in=pay_period_for(period_start, settings.PAY_PERIOD_ANCHOR)[1:],
                status=Timesheet.Status.APPROVED,
            )
        )
        if approval and approval.status == PeriodApproval.Status.APPROVED:
            before = {
                "status": approval.status,
                "approver": approval.approver.employee_code if approval.approver else None,
                "decided_at": approval.decided_at,
            }
            approval.status = PeriodApproval.Status.PENDING
            approval.approver = None
            approval.decided_at = None
            approval.save(update_fields=["status", "approver", "decided_at"])
            record(
                AuditLog.Action.UPDATE,
                "PeriodApproval",
                approval.pk,
                actor=actor,
                before=before,
                after={"status": approval.status},
                change_request=change_request,
            )
        for week in weeks:
            week.status = Timesheet.Status.SUBMITTED
            week.save(update_fields=["status"])
            supersede_payroll_week(week, actor=actor, at=at)
        return weeks


def unlock_week(timesheet, *, actor, change_request=None, at):
    """REOPENED until the later of +48 h and the week's Saturday 12:00 (D-21, D-50)."""
    with transaction.atomic():
        before = {"status": timesheet.status, "reopen_until": timesheet.reopen_until}
        if timesheet.status == Timesheet.Status.APPROVED:
            period_start = pay_period_for(timesheet.week_start, settings.PAY_PERIOD_ANCHOR)[0]
            reset_approval(
                timesheet.employee, period_start, actor=actor, change_request=change_request, at=at
            )
        timesheet.status = Timesheet.Status.REOPENED
        timesheet.reopen_until = reopen_until_for(timesheet.week_start, at)
        timesheet.save(update_fields=["status", "reopen_until"])
        record(
            AuditLog.Action.UNLOCK,
            "Timesheet",
            timesheet.pk,
            actor=actor,
            before=before,
            after={"status": timesheet.status, "reopen_until": timesheet.reopen_until},
            change_request=change_request,
        )
    return timesheet


# --- Phase 7: biweekly approval (FR-7) ----------------------------------------------------


def publish_payroll_period(approval, *, actor, at):
    """Payroll hook (D-61): called inside the approve transaction, once per approved period.

    Phase 8 replaces this body with payroll/services/publish.py → publish_period(approval),
    which writes one PayrollWeek per approved week into the payroll database. Until then
    nothing is written anywhere.
    """
    return None


@dataclass
class WeekView:
    number: int  # 1 or 2
    state: WeekState
    summary: WeekSummary
    open_request: ChangeRequest | None = None

    @property
    def week_start(self):
        return self.state.week_start

    @property
    def sheet(self):
        return self.state.timesheet

    @property
    def required(self):
        """Weeks with at least one employed day must be SUBMITTED; others don't count (D-56)."""
        return self.state.status != OUTSIDE_EMPLOYMENT


@dataclass
class PeriodRow:
    employee: Employee
    period_start: date
    weeks: list
    approval: PeriodApproval | None
    flags: dict = field(default_factory=dict)
    blockers: list = field(default_factory=list)

    @property
    def status(self):
        return self.approval.status if self.approval else PeriodApproval.Status.PENDING

    @property
    def worked(self):
        return sum(w.summary.worked for w in self.weeks)

    @property
    def leave(self):
        return sum(w.summary.leave for w in self.weeks)

    @property
    def can_decide(self):
        return not self.blockers

    @property
    def can_bulk(self):
        """Clean rows only: approvable now and no flags (D-63)."""
        return self.can_decide and not any(self.flags.values())


def approvable_employees(viewer):
    """Everyone the viewer may approve: direct reports, plus no-manager staff for admins (D-11)."""
    people = Employee.objects.filter(manager=viewer)
    if viewer.is_admin:
        people = people | Employee.objects.filter(manager__isnull=True)
    return people.exclude(pk=viewer.pk).select_related("team").order_by("last_name", "first_name")


def period_rows(viewer, period_start, now):
    """One row per approvable employee in the period (D-54).

    Active employees employed on at least one day of the period; inactive employees only if
    they have a timesheet in it (their existing timesheets can still be approved, D-19).
    """
    days = [period_start + timedelta(days=i) for i in range(14)]
    starts = pay_period_for(period_start, settings.PAY_PERIOD_ANCHOR)[1:]
    candidates = [e for e in approvable_employees(viewer) if any(employed_on(e, d) for d in days)]
    with_sheets = set(
        Timesheet.objects.filter(employee__in=candidates, week_start__in=starts).values_list(
            "employee_id", flat=True
        )
    )
    people = [e for e in candidates if e.status == Employee.Status.ACTIVE or e.pk in with_sheets]
    return _build_rows(people, period_start, now)


def period_row(viewer, employee, period_start, now):
    """The detail page's row; 403 unless the viewer may approve this employee (D-11)."""
    if not can_approve(viewer, employee):
        raise PermissionDenied("Only the employee's approver can open this period.")
    return _build_rows([employee], period_start, now)[0]


def _build_rows(people, period_start, now):
    starts = pay_period_for(period_start, settings.PAY_PERIOD_ANCHOR)[1:]
    sheets = {
        (s.employee_id, s.week_start): s
        for s in Timesheet.objects.filter(
            employee__in=people, week_start__in=starts
        ).prefetch_related("entries")
    }
    approvals = {
        a.employee_id: a
        for a in PeriodApproval.objects.filter(
            employee__in=people, period_start=period_start
        ).select_related("approver")
    }
    open_requests = {
        c.timesheet_id: c
        for c in ChangeRequest.objects.filter(
            timesheet__in=sheets.values(), status=ChangeRequest.Status.OPEN
        )
    }
    today = now.astimezone(company_tz()).date()
    rows = []
    for employee in people:
        weeks = []
        for number, start in enumerate(starts, start=1):
            sheet = sheets.get((employee.pk, start))
            entries = list(sheet.entries.all()) if sheet else []
            weeks.append(
                WeekView(
                    number=number,
                    state=week_state(employee, start, sheet, now),
                    summary=summarize(entries, employee, start),
                    open_request=open_requests.get(sheet.pk) if sheet else None,
                )
            )
        row = PeriodRow(employee, period_start, weeks, approvals.get(employee.pk))
        row.flags = _flags(row, today)
        row.blockers = _blockers(row)
        rows.append(row)
    return rows


def _flags(row, today):
    """Late, overtime and missing days (D-55); Hours worked never includes Break."""
    required = [w for w in row.weeks if w.required]
    missing = sum(
        1
        for w in required
        for d in w.summary.days
        if d.expected > 0 and d.total == 0 and d.day <= today
    )
    return {
        "late": any(w.sheet is not None and w.sheet.is_late for w in required),
        "overtime": any(w.summary.worked > w.summary.expected for w in required),
        "missing_days": missing,
    }


BLOCKED_BY_STATUS = {
    Timesheet.Status.LOCKED: "Week {n} is locked — unlock it first.",
    Timesheet.Status.REOPENED: "Week {n} is reopened — waiting for the employee to resubmit.",
    Timesheet.Status.DRAFT: "Week {n} hasn't been submitted yet.",
    "NOT_STARTED": "Week {n} hasn't been submitted yet.",
    Timesheet.Status.APPROVED: "Week {n} is already approved.",
}


def _blockers(row):
    """Why Approve / Reject can't be used right now; empty list = they can (D-06, D-56–D-58)."""
    if row.status == PeriodApproval.Status.APPROVED:
        return ["This period is already approved."]
    blockers = []
    for week in row.weeks:
        if week.required and week.state.status != Timesheet.Status.SUBMITTED:
            blockers.append(BLOCKED_BY_STATUS[week.state.status].format(n=week.number))
        if week.open_request:
            blockers.append(f"Handle the open change request on week {week.number} first.")
    if not any(w.required for w in row.weeks):
        blockers.append("The employee wasn't employed during this period.")
    return blockers


def approve_period(viewer, employee, period_start, *, now):
    """APPROVED: PeriodApproval + both weeks + audit + payroll hook, in one transaction."""
    with transaction.atomic():
        row = period_row(viewer, employee, period_start, now)
        if row.blockers:
            raise ValidationError(row.blockers)
        approval, _ = PeriodApproval.objects.select_for_update().get_or_create(
            employee=employee, period_start=period_start
        )
        before = {"status": approval.status, "weeks": _week_statuses(row)}
        approval.status = PeriodApproval.Status.APPROVED
        approval.approver = viewer
        approval.decided_at = now
        approval.comment = ""
        approval.save(update_fields=["status", "approver", "decided_at", "comment"])
        for week in row.weeks:
            if week.required:
                week.sheet.status = Timesheet.Status.APPROVED
                week.sheet.save(update_fields=["status"])
        record(
            AuditLog.Action.APPROVE,
            "PeriodApproval",
            approval.pk,
            actor=viewer,
            before=before,
            after={
                "status": approval.status,
                "weeks": _week_statuses(row),
                "worked_minutes": row.worked,
                "leave_minutes": row.leave,
            },
        )
        publish_payroll_period(approval, actor=viewer, at=now)
    return approval


def reject_period(viewer, employee, period_start, comment, *, now):
    """REJECTED with a required comment; required weeks REOPENED per D-21 (D-07, D-57)."""
    comment = (comment or "").strip()
    with transaction.atomic():
        row = period_row(viewer, employee, period_start, now)
        problems = list(row.blockers)
        if not comment:
            problems.append("Write a comment so the employee knows what to fix.")
        if problems:
            raise ValidationError(problems)
        approval, _ = PeriodApproval.objects.select_for_update().get_or_create(
            employee=employee, period_start=period_start
        )
        before = {"status": approval.status, "weeks": _week_statuses(row)}
        approval.status = PeriodApproval.Status.REJECTED
        approval.approver = viewer
        approval.decided_at = now
        approval.comment = comment
        approval.save(update_fields=["status", "approver", "decided_at", "comment"])
        reopened = {}
        for week in row.weeks:
            if week.required:
                sheet = week.sheet
                sheet.status = Timesheet.Status.REOPENED
                sheet.reopen_until = reopen_until_for(sheet.week_start, now)
                sheet.manager_note = comment
                sheet.save(update_fields=["status", "reopen_until", "manager_note"])
                reopened[sheet.week_start.isoformat()] = sheet.reopen_until
        record(
            AuditLog.Action.REJECT,
            "PeriodApproval",
            approval.pk,
            actor=viewer,
            before=before,
            after={"status": approval.status, "comment": comment, "reopen_until": reopened},
        )
    return approval


def _week_statuses(row):
    return {w.week_start.isoformat(): w.state.status for w in row.weeks if w.required}


def bulk_approve(viewer, period_start, codes, *, now):
    """Approve each ticked employee in its own transaction; returns (approved, skipped) (D-63).

    Every posted row is re-checked on the server: only clean rows (no blockers, no flags).
    """
    approved, skipped = [], []
    people = {e.employee_code: e for e in approvable_employees(viewer)}
    for code in dict.fromkeys(codes):  # keep order, drop duplicates
        employee = people.get(code)
        if employee is None:
            skipped.append((code, "You can't approve this employee."))
            continue
        name = f"{employee.first_name} {employee.last_name}"
        row = period_row(viewer, employee, period_start, now)
        if not row.can_bulk:
            reason = " ".join(row.blockers) or "Has flags — open the period to review it."
            skipped.append((name, reason))
            continue
        try:
            approve_period(viewer, employee, period_start, now=now)
        except ValidationError as exc:
            skipped.append((name, " ".join(exc.messages)))
        else:
            approved.append(name)
    return approved, skipped


def period_resubmitted(employee, week_start, *, at):
    """A week of a REJECTED period was resubmitted: the period is PENDING again (D-60)."""
    period_start = pay_period_for(week_start, settings.PAY_PERIOD_ANCHOR)[0]
    approval = (
        PeriodApproval.objects.select_for_update()
        .filter(employee=employee, period_start=period_start, status=PeriodApproval.Status.REJECTED)
        .first()
    )
    if approval is None:
        return None
    approval.status = PeriodApproval.Status.PENDING
    approval.save(update_fields=["status"])
    record(
        AuditLog.Action.UPDATE,
        "PeriodApproval",
        approval.pk,
        actor=employee,
        before={"status": PeriodApproval.Status.REJECTED},
        after={"status": approval.status, "resubmitted_week": week_start},
    )
    return approval


def approval_for_week(timesheet):
    """The PeriodApproval of the period this week belongs to, if any (week page status)."""
    if timesheet is None:
        return None
    period_start = pay_period_for(timesheet.week_start, settings.PAY_PERIOD_ANCHOR)[0]
    return (
        PeriodApproval.objects.filter(employee=timesheet.employee, period_start=period_start)
        .select_related("approver")
        .first()
    )
