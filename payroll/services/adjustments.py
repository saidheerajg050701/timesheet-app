"""Automatic pay adjustments (Change 4, D-118–D-122).

Once any version of an employee-week has been exported, its money flows through the original
payment plus adjustments: every later version is SETTLED (never exported as a week row again)
and an adjustment for "new version − previous version" is carried forward to the next pay run.
"""

from dataclasses import dataclass
from datetime import timedelta

from payroll.models import PayrollAdjustment, PayrollWeek
from timesheets.models import ChangeRequest
from timesheets.services.calendar import default_period

DEFAULT_REASON = "Re-approved after a change"
PERIOD = timedelta(weeks=2)
AMOUNT_FIELDS = tuple(f"{name}_minutes" for name in PayrollAdjustment.AMOUNTS)


def versions(employee_code, week_start):
    return PayrollWeek.objects.filter(employee_code=employee_code, week_start=week_start)


def ever_exported(record):
    """Was an earlier version of this record's week ever exported (and so paid or due)?"""
    earlier = versions(record.employee_code, record.week_start).filter(version__lt=record.version)
    return earlier.filter(exported_at__isnull=False).exists()


def previous_version(record):
    earlier = versions(record.employee_code, record.week_start).filter(version__lt=record.version)
    return earlier.order_by("-version").first()


def period_exported(period_start):
    """Has a batch already been exported for this pay period (weeks or adjustments)?"""
    return (
        PayrollWeek.objects.filter(period_start=period_start).exclude(export_batch="").exists()
        or PayrollAdjustment.objects.filter(period_start=period_start)
        .exclude(export_batch="")
        .exists()
    )


def carry_period(week_period_start, at):
    """The pay period an adjustment is carried to (D-121): from the later of the period after
    the corrected week's own period and the most recent completed period at `at`, the first
    one that has no export batch yet."""
    period = max(week_period_start + PERIOD, default_period(at))
    while period_exported(period):
        period += PERIOD
    return period


def reason_for(record):
    """The latest handled change request on the week's timesheet, if any (D-122)."""
    handled = (
        ChangeRequest.objects.filter(timesheet_id=record.source_timesheet_id)
        .exclude(status=ChangeRequest.Status.OPEN)
        .exclude(status=ChangeRequest.Status.REJECTED)
        .order_by("-resolved_at", "-pk")
        .first()
    )
    return handled.reason if handled else DEFAULT_REASON


@dataclass
class Settled:
    record: PayrollWeek
    adjustment: PayrollAdjustment | None


def settle(record, *, at):
    """Settle a new version of a once-exported week and create its adjustment (D-118, D-119).

    Returns Settled, or None when the week was never exported (today's behaviour: the version
    stays CURRENT and is exported normally). Idempotent: an already settled version only gets
    its missing adjustment, never a second one. Run inside a payroll transaction.
    """
    if record.status not in (PayrollWeek.Status.CURRENT, PayrollWeek.Status.SETTLED):
        return None
    if not ever_exported(record):
        return None
    if record.status == PayrollWeek.Status.CURRENT:
        record.status = PayrollWeek.Status.SETTLED
        record.settled_at = at
        record.save()
    exists = PayrollAdjustment.objects.filter(
        employee_code=record.employee_code,
        week_start=record.week_start,
        new_version=record.version,
    ).exists()
    old = previous_version(record)
    difference = {f: getattr(record, f) - getattr(old, f) for f in AMOUNT_FIELDS}
    if exists or not any(difference.values()):
        return Settled(record, None)  # nothing new to pay (zero difference, or done already)
    adjustment = PayrollAdjustment.objects.create(
        employee_code=record.employee_code,
        employee_name=record.employee_name,
        department=record.department,
        team=record.team,
        week_start=record.week_start,
        week_period_start=record.period_start,
        period_start=carry_period(record.period_start, at),
        old_version=old.version,
        new_version=record.version,
        approved_by_code=record.approved_by_code,
        approved_by_name=record.approved_by_name,
        approved_at=record.approved_at,
        reason=reason_for(record),
        source_timesheet_id=record.source_timesheet_id,
        **difference,
    )
    return Settled(record, adjustment)


def repair(*, at):
    """sync_payroll: settle every live version of a once-exported week that isn't settled yet
    and create missing adjustments (D-125). Returns the adjustments created."""
    created = []
    live = PayrollWeek.objects.filter(
        status__in=(PayrollWeek.Status.CURRENT, PayrollWeek.Status.SETTLED), version__gt=1
    ).order_by("employee_code", "week_start")
    for record in live:
        result = settle(record, at=at)
        if result and result.adjustment:
            created.append(result.adjustment)
    return created
