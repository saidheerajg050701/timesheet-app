"""The only code that moves a week to or from APPROVED (D-10, B.9 #10).

Biweekly approval (FR-7, D-54–D-63): the approvals page rows, approve, reject, bulk approve,
plus the Phase 6 reset/unlock used by change requests. Every change here happens in one
transaction with its PeriodApproval. Since Change 9 the approver decides every required week
that is SUBMITTED or LOCKED (D-139); `decision_blockers` is the one rule for when they can.
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
    approval_deadline_for,
    company_tz,
    employed_on,
    pay_period_for,
    reopen_until_for,
    week_state,
)
from timesheets.services.summary import WeekSummary, summarize


def supersede_payroll_week(timesheet, *, actor, at):
    """Payroll hook (D-53): called for every week that leaves APPROVED.

    Registers payroll/services/publish.py → supersede_week to run after this transaction
    commits, in its own payroll transaction (D-65). Never writes to payroll while the main
    transaction can still roll back.
    """
    from payroll.services.publish import supersede_after_commit  # payroll depends on us

    supersede_after_commit(timesheet, actor=actor, at=at)


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
    """Payroll hook (D-61, D-65): called inside the approve transaction, once per period.

    Registers payroll/services/publish.py → publish_period to run after the approval has
    committed, in its own payroll transaction. If that fails, the approval stands and
    `manage.py sync_payroll` writes the missing records.
    """
    from payroll.services.publish import publish_after_commit  # payroll depends on us

    publish_after_commit(approval, actor=actor, at=at)


@dataclass
class WeekView:
    number: int  # 1 or 2
    state: WeekState
    summary: WeekSummary
    open_request: ChangeRequest | None = None
    missing_days: int = 0  # employed weekdays up to today with nothing entered (D-55)

    @property
    def week_start(self):
        return self.state.week_start

    @property
    def sheet(self):
        return self.state.timesheet

    @property
    def required(self):
        """Weeks with at least one employed day need a decision; others don't count (D-56)."""
        return self.state.status != OUTSIDE_EMPLOYMENT

    @property
    def hours(self):
        """What approving pays for this week: worked + leave minutes (Break never counts)."""
        return self.summary.worked + self.summary.leave

    @property
    def not_submitted_by_employee(self):
        """Locked or approved without the employee ever submitting it: no submission time
        (D-141). The same fact makes the week count as missed (D-75)."""
        return (
            self.required
            and self.state.status in (Timesheet.Status.LOCKED, Timesheet.Status.APPROVED)
            and (self.sheet is None or self.sheet.submitted_at is None)
        )


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
    def unsubmitted_weeks(self):
        """Required weeks that would be approved although the employee never submitted them."""
        return [w for w in self.weeks if w.required and w.state.status == Timesheet.Status.LOCKED]

    @property
    def can_bulk(self):
        """Clean rows only: approvable now, no flags, no locked week (D-63, D-139)."""
        return self.can_decide and not any(self.flags.values()) and not self.unsubmitted_weeks


def approvable_employees(viewer):
    """Everyone the viewer may approve: direct reports, plus no-manager staff for admins (D-11)."""
    people = Employee.objects.filter(manager=viewer)
    if viewer.is_admin:
        people = people | Employee.objects.filter(manager__isnull=True)
    return people.exclude(pk=viewer.pk).select_related("team").order_by("last_name", "first_name")


def must_be_approved(employees, period_start):
    """Who among `employees` must be approved for the period — the one rule (D-54, D-134).

    Active employees employed on at least one day of the period; inactive employees only if
    they have a timesheet in it (their existing timesheets can still be approved, D-19).
    """
    days = [period_start + timedelta(days=i) for i in range(14)]
    starts = pay_period_for(period_start, settings.PAY_PERIOD_ANCHOR)[1:]
    candidates = [e for e in employees if any(employed_on(e, d) for d in days)]
    with_sheets = set(
        Timesheet.objects.filter(employee__in=candidates, week_start__in=starts).values_list(
            "employee_id", flat=True
        )
    )
    return [e for e in candidates if e.status == Employee.Status.ACTIVE or e.pk in with_sheets]


def period_rows(viewer, period_start, now):
    """One row per approvable employee in the period (D-54)."""
    people = must_be_approved(approvable_employees(viewer), period_start)
    return _build_rows(people, period_start, now)


def company_period_rows(period_start, now):
    """Everyone in the company who must be approved for the period: together, every approver's
    list (direct manager, or an admin for no-manager staff, D-11). For the pay register (D-134)."""
    people = Employee.objects.select_related("team", "manager__team").order_by(
        "last_name", "first_name"
    )
    return _build_rows(must_be_approved(people, period_start), period_start, now)


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
            week = WeekView(
                number=number,
                state=week_state(employee, start, sheet, now),
                summary=summarize(entries, employee, start),
                open_request=open_requests.get(sheet.pk) if sheet else None,
            )
            if week.required:
                week.missing_days = sum(
                    1
                    for d in week.summary.days
                    if d.expected > 0 and d.total == 0 and d.day <= today
                )
            weeks.append(week)
        row = PeriodRow(employee, period_start, weeks, approvals.get(employee.pk))
        row.flags = _flags(row)
        row.blockers = decision_blockers(row)
        rows.append(row)
    return rows


def _flags(row):
    """Late, overtime and missing days (D-55); Hours worked never includes Break."""
    required = [w for w in row.weeks if w.required]
    return {
        "late": any(w.sheet is not None and w.sheet.is_late for w in required),
        "overtime": any(w.summary.worked > w.summary.expected for w in required),
        "missing_days": sum(w.missing_days for w in required),
    }


DECIDABLE = (Timesheet.Status.SUBMITTED, Timesheet.Status.LOCKED)  # D-139


def week_blocker(row, week):
    """Why the approver can't act on this required week yet, or "" (D-139)."""
    status = week.state.status
    if status == Timesheet.Status.REOPENED:
        until = week.sheet.reopen_until.astimezone(company_tz())
        return (
            f"Week {week.number} is reopened until {until:%a %b %-d, %-I:%M %p} — waiting for "
            f"{row.employee.first_name} to resubmit."
        )
    if status in (Timesheet.Status.DRAFT, "NOT_STARTED"):
        return f"Week {week.number} hasn't been submitted yet."
    if status not in DECIDABLE:
        return f"Week {week.number} is already approved."
    return ""


def decision_blockers(row):
    """Why Approve / Reject can't be used right now; empty list = they can (D-56–D-58, D-139).

    Every required week must be SUBMITTED or LOCKED (a locked week is decided with the hours
    entered so far); a REOPENED week waits for the employee until its window ends; an open
    change request still blocks.
    """
    if row.status == PeriodApproval.Status.APPROVED:
        return ["This period is already approved."]
    blockers = []
    for week in row.weeks:
        if week.required and (problem := week_blocker(row, week)):
            blockers.append(problem)
        if week.open_request:
            blockers.append(f"Handle the open change request on week {week.number} first.")
    if not any(w.required for w in row.weeks):
        blockers.append("The employee wasn't employed during this period.")
    return blockers


def edit_blockers(row, week):
    """Why the approver can't edit this week from Approvals, or [] (D-140)."""
    if row.status == PeriodApproval.Status.APPROVED:
        return ["This period is already approved — corrections go through a change request."]
    if not week.required:
        return ["The employee wasn't employed this week."]
    problems = [p for p in (week_blocker(row, week),) if p]
    if week.open_request:
        problems.append(f"Handle the open change request on week {week.number} first.")
    return problems


def unsubmitted_notes(row):
    """What the Approve confirmation says for weeks the employee never submitted (D-141)."""
    name = f"{row.employee.first_name} {row.employee.last_name}"
    notes = []
    for week in row.unsubmitted_weeks:
        notes.append(
            f"Week {week.number} was not submitted by {name}; it will be approved with "
            f"{week.hours / 60:.2f} hours."
        )
        if not week.hours:
            notes.append(f"Week {week.number} has 0.00 hours.")
        if week.missing_days:
            days = week.missing_days
            notes.append(f"Week {week.number} has {days} missing day{'' if days == 1 else 's'}.")
    return notes


def _sheet_for(employee, week):
    """The week's timesheet; a locked week nobody ever opened gets one now (as Unlock does)."""
    if week.sheet is not None:
        return week.sheet
    return Timesheet.objects.create(
        employee=employee, week_start=week.week_start, status=Timesheet.Status.LOCKED
    )


def approve_period(viewer, employee, period_start, *, now, confirm_unsubmitted=False):
    """APPROVED: PeriodApproval + both weeks + audit + payroll hook, in one transaction.

    A LOCKED week is approved with the hours entered so far, only with `confirm_unsubmitted`
    (the approver saw the confirmation, D-141); it keeps no submission time, so it stays
    "not submitted by employee" and still counts as missed (D-75).
    """
    with transaction.atomic():
        row = period_row(viewer, employee, period_start, now)
        if row.blockers:
            raise ValidationError(row.blockers)
        unsubmitted = [w.week_start.isoformat() for w in row.unsubmitted_weeks]
        if unsubmitted and not confirm_unsubmitted:
            raise ValidationError(
                [*unsubmitted_notes(row), "Confirm to approve the weeks that weren't submitted."]
            )
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
                sheet = _sheet_for(employee, week)
                sheet.status = Timesheet.Status.APPROVED
                sheet.save(update_fields=["status"])
        after = {
            "status": approval.status,
            "weeks": _week_statuses(row),
            "worked_minutes": row.worked,
            "leave_minutes": row.leave,
        }
        if unsubmitted:
            after["not_submitted_by_employee"] = unsubmitted
        record(
            AuditLog.Action.APPROVE,
            "PeriodApproval",
            approval.pk,
            actor=viewer,
            before=before,
            after=after,
            at=now,  # the decision time, as PeriodApproval.decided_at
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
                sheet = _sheet_for(employee, week)
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


# --- who still has to approve (Change 9, D-143) ---------------------------------------------


def person_state(row):
    """Where a not-yet-approved person stands, in words, for payroll and HR."""
    required = [w for w in row.weeks if w.required]
    if any(w.open_request for w in row.weeks):
        return "Change request open"
    reopened = [w for w in required if w.state.status == Timesheet.Status.REOPENED]
    if reopened:
        until = min(w.sheet.reopen_until for w in reopened).astimezone(company_tz())
        return f"Reopened until {until:%a %b %-d, %-I:%M %p}"
    if any(w.state.status == Timesheet.Status.LOCKED for w in required):
        return "Locked – not submitted"
    if any(w.state.status in (Timesheet.Status.DRAFT, "NOT_STARTED") for w in required):
        return "Not submitted yet"
    return "Submitted"


@dataclass
class ManagerGroup:
    """One approver's part of the period: everyone they must approve, and who is still open."""

    approver: Employee | None  # None: staff with no manager, approved by an admin (D-11)
    pending: list = field(default_factory=list)  # [(PeriodRow, state)], by name
    total: int = 0

    @property
    def label(self):
        if self.approver is None:
            return "HR / admins"
        return f"{self.approver.first_name} {self.approver.last_name}"

    @property
    def team(self):
        team = self.approver.team if self.approver else None
        return team.name if team else ""

    @property
    def done(self):
        return not self.pending


@dataclass
class PendingReport:
    period_start: date
    deadline: object
    overdue: bool  # the approval deadline has passed: pending people are Overdue (D-133)
    groups: list  # ManagerGroup, by approver name

    @property
    def open_groups(self):
        return [g for g in self.groups if not g.done]

    @property
    def required(self):
        return sum(g.total for g in self.groups)

    @property
    def approved(self):
        return self.required - sum(len(g.pending) for g in self.groups)

    @property
    def managers_done(self):
        return sum(g.done for g in self.groups)


def pending_by_manager(period_start, now):
    """Who still has people to approve in the period — the same rows and rule as Approvals
    (company_period_rows, decision_blockers). Read only (D-143)."""
    groups = {}
    for row in company_period_rows(period_start, now):
        manager = row.employee.manager
        group = groups.setdefault(row.employee.manager_id, ManagerGroup(manager))
        group.total += 1
        if row.status != PeriodApproval.Status.APPROVED:
            group.pending.append((row, person_state(row)))
    deadline = approval_deadline_for(period_start)
    ordered = sorted(groups.values(), key=lambda g: (g.approver is None, g.label))
    return PendingReport(period_start, deadline, now >= deadline, ordered)


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
