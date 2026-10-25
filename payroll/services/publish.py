"""Writing approved weeks into the payroll database (FR-11, B.9 #13, D-65, D-66).

The main database decides; payroll follows. The timesheet hooks call publish_after_commit /
supersede_after_commit, which run only after the main transaction has committed, each in its
own payroll transaction. If a payroll write fails, nothing partial is left behind, the error
is logged, and `manage.py sync_payroll` repairs it.
"""

import logging
from dataclasses import dataclass, field
from functools import partial

from django.conf import settings
from django.db import transaction
from django.db.models import Max

from audit.models import AuditLog
from audit.services.log import build, bulk_record
from payroll.models import PayrollWeek
from payroll.services.adjustments import settle
from payroll.services.hours import split_hours
from timesheets.models import PeriodApproval, Timesheet
from timesheets.services.calendar import expected_minutes_for, pay_period_for

logger = logging.getLogger(__name__)
REPAIR_HINT = "run `uv run python manage.py sync_payroll` to repair"


@dataclass
class PublishResult:
    created: list = field(default_factory=list)
    superseded: list = field(default_factory=list)
    adjustments: list = field(default_factory=list)  # carried to a later pay run (D-119)


def live_records(employee_code, week_start):
    return PayrollWeek.objects.filter(employee_code=employee_code, week_start=week_start).exclude(
        status=PayrollWeek.Status.SUPERSEDED
    )


def snapshot(approval, sheet):
    """The frozen fields of one week's record (D-15, D-71)."""
    employee = sheet.employee
    expected = expected_minutes_for(employee, sheet.week_start)
    split = split_hours(list(sheet.entries.all()), expected)
    approver = approval.approver
    return {
        "employee_code": employee.employee_code,
        "employee_name": f"{employee.first_name} {employee.last_name}",
        "department": employee.team.department if employee.team else "",
        "team": employee.team.name if employee.team else "",
        "week_start": sheet.week_start,
        "period_start": approval.period_start,
        "regular_minutes": split.regular,
        "overtime_minutes": split.overtime,
        "pto_minutes": split.pto,
        "sick_minutes": split.sick,
        "holiday_minutes": split.holiday,
        "total_minutes": split.total,
        "expected_weekly_minutes": expected,
        "approved_by_code": approver.employee_code if approver else "",
        "approved_by_name": f"{approver.first_name} {approver.last_name}" if approver else "",
        "approved_at": approval.decided_at,
        "source_timesheet_id": sheet.pk,
    }


def next_version(employee_code, week_start):
    found = PayrollWeek.objects.filter(employee_code=employee_code, week_start=week_start)
    return (found.aggregate(top=Max("version"))["top"] or 0) + 1


def publish_period(approval, *, actor=None, system_actor="", at):
    """One record per approved week of an APPROVED period. Idempotent (T-35, D-66).

    A week already published for this decision (same approved_at) is skipped. A live record
    from an older decision is superseded and the next version written. If an earlier version of
    the week was already exported, the new one is SETTLED and its difference becomes an
    adjustment for the next pay run, in the same payroll transaction (D-118–D-121).
    """
    approval = PeriodApproval.objects.select_related("employee__team", "approver").get(
        pk=approval.pk
    )
    result = PublishResult()
    if approval.status != PeriodApproval.Status.APPROVED:
        return result
    weeks = pay_period_for(approval.period_start, settings.PAY_PERIOD_ANCHOR)[1:]
    sheets = (
        Timesheet.objects.filter(
            employee=approval.employee, week_start__in=weeks, status=Timesheet.Status.APPROVED
        )
        .select_related("employee__team")
        .prefetch_related("entries")
        .order_by("week_start")
    )
    code = approval.employee.employee_code
    with transaction.atomic(using="payroll"):
        for sheet in sheets:
            live = live_records(code, sheet.week_start).first()
            if live and live.approved_at == approval.decided_at:
                continue  # already published for this decision
            if live:
                result.superseded.append(_supersede(live, at))
            version = next_version(code, sheet.week_start)
            record = PayrollWeek.objects.create(**snapshot(approval, sheet), version=version)
            result.created.append(record)
            settled = settle(record, at=at)
            if settled and settled.adjustment:
                result.adjustments.append(settled.adjustment)
    audit_result(result, actor=actor, system_actor=system_actor, at=at)
    return result


def supersede_week(employee_code, week_start, *, actor=None, system_actor="", at):
    """The week left APPROVED (edit or unlock): its live record becomes SUPERSEDED (D-15)."""
    result = PublishResult()
    with transaction.atomic(using="payroll"):
        for record in live_records(employee_code, week_start):
            result.superseded.append(_supersede(record, at))
    audit_result(result, actor=actor, system_actor=system_actor, at=at)
    return result


def _supersede(record, at):
    record.status = PayrollWeek.Status.SUPERSEDED
    record.superseded_at = at
    record.save()
    return record


def audit_result(result, *, actor=None, system_actor="", at):
    rows = (
        [
            build(
                AuditLog.Action.SUPERSEDE,
                "PayrollWeek",
                r.pk,
                actor=actor,
                system_actor=system_actor,
                after={
                    "employee_code": r.employee_code,
                    "week_start": r.week_start,
                    "version": r.version,
                },
                at=at,
            )
            for r in result.superseded
        ]
        + [
            build(
                AuditLog.Action.PUBLISH,
                "PayrollWeek",
                r.pk,
                actor=actor,
                system_actor=system_actor,
                after={
                    "employee_code": r.employee_code,
                    "week_start": r.week_start,
                    "version": r.version,
                    "regular_minutes": r.regular_minutes,
                    "overtime_minutes": r.overtime_minutes,
                    "total_minutes": r.total_minutes,
                },
                at=at,
            )
            for r in result.created
        ]
        + [
            adjustment_audit(a, actor=actor, system_actor=system_actor, at=at)
            for a in result.adjustments
        ]
    )
    if rows:
        bulk_record(rows)


def adjustment_audit(adjustment, *, actor=None, system_actor="", at):
    """PUBLISH row for a new adjustment (D-125); the reason stays out of the audit summary."""
    return build(
        AuditLog.Action.PUBLISH,
        "PayrollAdjustment",
        adjustment.pk,
        actor=actor,
        system_actor=system_actor,
        after={
            "employee_code": adjustment.employee_code,
            "week_start": adjustment.week_start,
            "versions": [adjustment.old_version, adjustment.new_version],
            "period_start": adjustment.period_start,
            **{f"{n}_minutes": getattr(adjustment, f"{n}_minutes") for n in adjustment.AMOUNTS},
        },
        at=at,
    )


# --- called by the timesheet hooks, after the main database commits (D-65) ----------------


def publish_after_commit(approval, *, actor, at):
    transaction.on_commit(
        partial(_run_safely, "publish", publish_period, approval, actor=actor, at=at),
        using="default",
        robust=True,
    )


def supersede_after_commit(timesheet, *, actor, at):
    code, week = timesheet.employee.employee_code, timesheet.week_start
    transaction.on_commit(
        partial(_run_safely, "supersede", supersede_week, code, week, actor=actor, at=at),
        using="default",
        robust=True,
    )


def _run_safely(what, func, *args, **kwargs):
    """The main database has already committed; a payroll failure must not undo it."""
    try:
        return func(*args, **kwargs)
    except Exception:
        logger.exception(
            "Payroll %s failed after the timesheet change was saved; %s.", what, REPAIR_HINT
        )
        return None


def out_of_sync():
    """(approved weeks with no live record, live records whose week is no longer approved)."""
    approved = set(
        Timesheet.objects.filter(status=Timesheet.Status.APPROVED).values_list(
            "employee__employee_code", "week_start"
        )
    )
    live = set(
        PayrollWeek.objects.exclude(status=PayrollWeek.Status.SUPERSEDED).values_list(
            "employee_code", "week_start"
        )
    )
    return len(approved - live), len(live - approved)
