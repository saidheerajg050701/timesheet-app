"""Registers for periods exported before registers existed (D-137)."""

from django.db import transaction

from audit.models import AuditLog
from audit.services.log import record
from directory.models import Employee
from payroll.models import (
    PayrollAdjustment,
    PayrollRegister,
    PayrollWeek,
)
from payroll.services.register.actions import _save_lines
from payroll.services.register.constants import BACKFILL_ACTOR
from payroll.services.register.state import (
    Items,
    build_lines,
)
from timesheets.models import PeriodApproval
from timesheets.services.approvals import must_be_approved
from timesheets.services.calendar import period_end_for

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
