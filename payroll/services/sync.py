"""sync_payroll: bring the payroll database back in line with the main database (D-65)."""

from audit.models import AuditLog
from audit.services.log import record
from payroll.models import PayrollWeek
from payroll.services.publish import publish_period, supersede_week
from timesheets.models import PeriodApproval, Timesheet

SYSTEM_ACTOR = "sync_payroll"


def sync_payroll(*, at):
    """Publish every approved period (idempotent) and supersede records of weeks that are no
    longer approved. Returns (published, superseded) counts and writes one SYNC audit row.
    """
    published = superseded = 0
    approvals = PeriodApproval.objects.filter(status=PeriodApproval.Status.APPROVED).order_by(
        "period_start", "pk"
    )
    for approval in approvals:
        result = publish_period(approval, system_actor=SYSTEM_ACTOR, at=at)
        published += len(result.created)
        superseded += len(result.superseded)

    approved = set(
        Timesheet.objects.filter(status=Timesheet.Status.APPROVED).values_list(
            "employee__employee_code", "week_start"
        )
    )
    stale = {
        (r.employee_code, r.week_start)
        for r in PayrollWeek.objects.exclude(status=PayrollWeek.Status.SUPERSEDED)
    } - approved
    for code, week in sorted(stale):
        superseded += len(supersede_week(code, week, system_actor=SYSTEM_ACTOR, at=at).superseded)

    record(
        AuditLog.Action.SYNC,
        "Payroll",
        "sync",
        system_actor=SYSTEM_ACTOR,
        after={
            "approved_periods": approvals.count(),
            "published": published,
            "superseded": superseded,
        },
        at=at,
    )
    return published, superseded
