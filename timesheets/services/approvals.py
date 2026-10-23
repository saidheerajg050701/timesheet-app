"""The only code that moves a week to or from APPROVED (D-10, B.9 #10).

Phase 6 adds reset_approval and unlock_week; approve_period and reject_period arrive in
Phase 7. Every change here happens in one transaction with its PeriodApproval.
"""

from django.conf import settings
from django.db import transaction

from audit.models import AuditLog
from audit.services.log import record
from timesheets.models import PeriodApproval, Timesheet
from timesheets.services.calendar import pay_period_for, reopen_until_for


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
