"""The demo payroll database: publish, finalize, pay, one correction (B.7, D-137, D-144)."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.directory.models import Employee
from apps.directory.services.demo.constants import (
    HR,
    PAYROLL_CLERK,
    SYSTEM_ACTOR,
)
from apps.timesheets.models import PeriodApproval, Timesheet


def seed_payroll(now):
    """Publish every approved period; older periods' registers finalized & exported and paid,
    the next one finalized, the newest left to finalize; one correction (B.7, D-137)."""
    from apps.payroll.models import PayrollRegister, PayrollWeek
    from apps.payroll.services.publish import PublishResult, audit_result, publish_period, snapshot
    from apps.payroll.services.register import finalize, mark_paid

    tz = ZoneInfo(settings.COMPANY_TZ)
    approve_the_rest(now, tz)
    approvals = list(
        PeriodApproval.objects.filter(status=PeriodApproval.Status.APPROVED)
        .select_related("employee", "approver")
        .order_by("period_start", "employee__employee_code")
    )
    periods = sorted({a.period_start for a in approvals})
    paid, exported_only = periods[:-2], periods[-2:-1]
    correction = next((a for a in approvals if paid and a.period_start == paid[0]), None)
    clerk = Employee.objects.filter(employee_code=PAYROLL_CLERK).first()

    for approval in approvals:
        if approval is not correction:
            publish_period(approval, actor=approval.approver, at=approval.decided_at)
            continue
        # The correction (B.7): week 1 was first published with an hour less, from an earlier
        # decision; it is exported and paid with its period, then superseded below.
        sheets = Timesheet.objects.filter(
            employee=approval.employee,
            week_start__in=(approval.period_start, approval.period_start + timedelta(weeks=1)),
        ).order_by("week_start")
        first = []
        for number, sheet in enumerate(sheets, start=1):
            fields = snapshot(approval, sheet)
            if number == 1:
                fields["regular_minutes"] -= 60
                fields["total_minutes"] -= 60
                fields["approved_at"] = approval.decided_at - timedelta(days=2)
            first.append(PayrollWeek.objects.create(**fields, version=1))
        audit_result(
            PublishResult(created=first), actor=approval.approver, at=fields["approved_at"]
        )

    for period in paid + exported_only:  # the approval deadlines have passed: READY
        exported_at = datetime.combine(period + timedelta(days=19), time(10), tzinfo=tz)  # Fri
        finalize(period, actor=clerk, now=exported_at)
        if period in paid:
            mark_paid(period, actor=clerk, at=exported_at + timedelta(days=7))
    if correction:
        fixed_at = datetime.combine(
            correction.period_start + timedelta(days=29),
            time(10),
            tzinfo=tz,  # a Monday
        )
        publish_period(correction, system_actor=SYSTEM_ACTOR, at=min(fixed_at, now))
    return {
        "records": PayrollWeek.objects.count(),
        "registers": PayrollRegister.objects.count(),
        "paid_registers": PayrollRegister.objects.filter(status="PAID").count(),
        "corrections": PayrollWeek.objects.filter(status=PayrollWeek.Status.SUPERSEDED).count(),
    }


def approve_the_rest(now, tz):
    """Older periods are fully approved (Change 9, D-144): each manager also approves the
    people the history left pending — a week locked without a submission (approved with what
    was entered, still "not submitted by employee" and missed), or no timesheet at all (sign-up
    candidates) — through the real approvals service. The most recent completed period stays
    pending (B.7). Payroll is published right after, with everything else."""
    from apps.timesheets.services.approvals import approve_period, company_period_rows
    from apps.timesheets.services.calendar import default_period

    hr = Employee.objects.get(employee_code=HR)
    last_completed = default_period(now)
    older = PeriodApproval.objects.filter(period_start__lt=last_completed)
    for period in sorted(set(older.values_list("period_start", flat=True))):
        decided = datetime.combine(period + timedelta(days=16), time(15), tzinfo=tz)  # Tuesday
        for row in company_period_rows(period, decided):
            if row.status == PeriodApproval.Status.APPROVED or row.blockers:
                continue
            approver = row.employee.manager or hr  # the CEO is approved by HR (D-11)
            approve_period(approver, row.employee, period, now=decided, confirm_unsubmitted=True)
