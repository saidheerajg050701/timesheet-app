"""sync_payroll: bring the payroll database back in line with the main database (D-65)."""

from dataclasses import dataclass

from django.db import transaction

from apps.audit.models import AuditLog
from apps.audit.services.log import bulk_record, record
from apps.payroll.models import PayrollWeek
from apps.payroll.services.adjustments import repair
from apps.payroll.services.publish import adjustment_audit, publish_period, supersede_week
from apps.payroll.services.register import build_registers
from apps.timesheets.models import PeriodApproval, Timesheet

SYSTEM_ACTOR = "sync_payroll"


def sync_payroll(*, at):
    """Publish every approved period (idempotent), supersede records of weeks that are no
    longer approved, and settle corrected versions of once-exported weeks with their missing
    adjustments (D-125). Returns (published, superseded); see sync_payroll_counts.
    """
    published, superseded, _ = sync_payroll_counts(at=at)
    return published, superseded


def sync_payroll_counts(*, at):
    """sync_payroll, returning (published, superseded, adjustments) and writing one SYNC row."""
    result = sync_payroll_report(at=at)
    return result.published, result.superseded, result.adjustments


@dataclass
class SyncResult:
    published: int
    superseded: int
    adjustments: int
    registers: int  # registers built for periods exported before registers existed (D-137)


def sync_payroll_report(*, at):
    """The whole repair, idempotent: records, adjustments, then registers (D-125, D-137)."""
    published = superseded = 0
    approvals = PeriodApproval.objects.filter(status=PeriodApproval.Status.APPROVED).order_by(
        "period_start", "pk"
    )
    results = []
    for approval in approvals:
        result = publish_period(approval, system_actor=SYSTEM_ACTOR, at=at)
        results.append(result)
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
    adjustments = sum(len(r.adjustments) for r in results)
    with transaction.atomic(using="payroll"):
        repaired = repair(at=at)
    bulk_record([adjustment_audit(a, system_actor=SYSTEM_ACTOR, at=at) for a in repaired])
    adjustments += len(repaired)
    registers = len(build_registers(system_actor=SYSTEM_ACTOR, at=at))

    record(
        AuditLog.Action.SYNC,
        "Payroll",
        "sync",
        system_actor=SYSTEM_ACTOR,
        after={
            "approved_periods": approvals.count(),
            "published": published,
            "superseded": superseded,
            "adjustments": adjustments,
            "registers": registers,
        },
        at=at,
    )
    return SyncResult(published, superseded, adjustments, registers)
