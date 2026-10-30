"""Finalize & export and Mark as paid (D-135)."""

from django.core.exceptions import ValidationError
from django.db import transaction

from audit.models import AuditLog
from audit.services.log import record
from payroll.models import (
    PayrollAdjustment,
    PayrollRegister,
    PayrollRegisterLine,
    PayrollWeek,
)
from payroll.services.export import next_batch
from payroll.services.register.constants import READY
from payroll.services.register.state import (
    build_lines,
    period_items,
    period_state,
)
from timesheets.services.calendar import period_end_for

# --- Finalize & export, Mark as paid ----------------------------------------------------------


def _actor_fields(actor, system_actor):
    if actor is not None:
        return actor.employee_code, f"{actor.first_name} {actor.last_name}"
    return "", system_actor


def finalize(period_start, *, actor=None, system_actor="", now):
    """Finalize & export (D-135): only when READY. In one payroll transaction the lines are
    saved, and every week record and adjustment they pay becomes EXPORTED in one new batch.
    Returns the register."""
    state = period_state(period_start, now)
    if state.finalized:
        raise ValidationError("This pay period's register is already finalized.")
    if state.status != READY:
        raise ValidationError(state.waiting_for)
    code, name = _actor_fields(actor, system_actor)
    with transaction.atomic(using="payroll"):
        if PayrollRegister.objects.filter(period_start=period_start).exists():
            raise ValidationError("This pay period's register is already finalized.")
        items = period_items(period_start)
        lines = build_lines(period_start, items)
        batch = next_batch()
        for r in items.weeks + items.late + items.adjustments:
            r.status = r.Status.EXPORTED
            r.export_batch = batch
            r.exported_at = now
            r.save()
        register = PayrollRegister.objects.create(
            period_start=period_start,
            period_end=period_end_for(period_start),
            export_batch=batch,
            ready_reason=state.ready_reason,
            required_count=state.required,
            approved_count=state.approved,
            finalized_at=now,
            finalized_by_code=code,
            finalized_by_name=name,
        )
        _save_lines(register, lines)
    record(
        AuditLog.Action.EXPORT,
        "PayrollRegister",
        period_start.isoformat(),
        actor=actor,
        system_actor=system_actor,
        after={
            "period_start": period_start,
            "batch": batch,
            "lines": len(lines),
            "records": len(items.weeks) + len(items.late),
            "late_weeks": len(items.late),
            "adjustments": len(items.adjustments),
            "total_minutes": items.total,
        },
        at=now,
    )
    return register


def _save_lines(register, lines):
    for line in lines:
        line.register = register
        line.week_record_ids = [r.pk for r in line.week_records]
        line.adjustment_ids = [a.pk for a in line.adjustments]
    PayrollRegisterLine.objects.bulk_create(lines)


def mark_paid(period_start, *, actor=None, system_actor="", at):
    """Mark as paid (D-135): the register and the records of its batch become PAID, once.
    Returns (week records, adjustments) paid now, or None if it was already paid."""
    with transaction.atomic(using="payroll"):
        register = PayrollRegister.objects.get(period_start=period_start)
        if register.status == PayrollRegister.Status.PAID:
            return None
        weeks = list(
            PayrollWeek.objects.filter(
                export_batch__in=register.batches, status=PayrollWeek.Status.EXPORTED
            )
        )
        adjustments = list(
            PayrollAdjustment.objects.filter(
                export_batch__in=register.batches, status=PayrollAdjustment.Status.EXPORTED
            )
        )
        for r in weeks + adjustments:
            r.status = r.Status.PAID
            r.paid_at = at
            r.save()
        register.status = PayrollRegister.Status.PAID
        register.paid_at = at
        register.save()
    record(
        AuditLog.Action.PAY,
        "PayrollRegister",
        period_start.isoformat(),
        actor=actor,
        system_actor=system_actor,
        after={
            "period_start": period_start,
            "batch": register.export_batch,
            "records": len(weeks),
            "adjustments": len(adjustments),
        },
        at=at,
    )
    return len(weeks), len(adjustments)
