"""Payroll pages (FR-11): payroll staff and admins only (D-12). Only approved hours are shown —
never timesheet rows, notes or reasons. Each ended pay period has a register (Change 8,
D-132–D-138): previewed live while OPEN or READY, saved by "Finalize & export", then paid."""

import csv
import io
from datetime import date

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from directory.services.permissions import payroll_required
from payroll.models import PayrollAdjustment, PayrollRegister, PayrollWeek
from payroll.services.adjustments import closed_periods
from payroll.services.export import batches_csv, corrections, safe_cell
from payroll.services.publish import out_of_sync
from payroll.services.register import (
    READY,
    ended_periods,
    file_stem,
    finalize,
    mark_paid,
    period_state,
    preview,
    register_csv,
    table,
    unregistered_periods,
)
from timesheets.services.calendar import (
    current_period,
    period_end_for,
    period_ended,
    period_start_for,
)
from timesheets.services.pending import pending_by_manager

STATUS_CHOICES = [("", "All but superseded")] + list(PayrollWeek.Status.choices)


def _date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise Http404("Not a date.") from None


def _csv(text, filename):
    response = HttpResponse("\ufeff" + text, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _mark_settled_in(records):
    """Give each SETTLED week `settled_in`: the pay period its adjustment was carried to, or
    None when the correction changed nothing (D-124)."""
    settled = [r for r in records if r.status == PayrollWeek.Status.SETTLED]
    adjustments = PayrollAdjustment.objects.filter(
        employee_code__in={r.employee_code for r in settled},
        week_start__in={r.week_start for r in settled},
    )
    carried = {(a.employee_code, a.week_start, a.new_version): a.period_start for a in adjustments}
    for r in settled:
        r.settled_in = carried.get((r.employee_code, r.week_start, r.version))


def _out_of_sync():
    missing, stale = out_of_sync()
    return {"missing": missing, "stale": stale, "unregistered": len(unregistered_periods())}


@payroll_required
def payroll_home(request):
    """Every ended pay period, newest first, with its register's status (D-138)."""
    if request.GET.get("period"):  # older links (?period=…) open that period's register
        period = period_start_for(_date(request.GET["period"]))
        return redirect("payroll_period", period=period)
    now = timezone.now()
    closed = closed_periods()
    periods = [period_state(p, now, closed) for p in ended_periods(now)]
    return render(request, "payroll/home.html", {"periods": periods, **_out_of_sync()})


def _detail_tables(request, period):
    """The period's week records and adjustments, with the page's filters (D-124)."""
    filters = {
        key: request.GET.get(key, "").strip()
        for key in ("department", "team", "employee", "status")
    }
    records = PayrollWeek.objects.filter(period_start=period)
    adjustments = PayrollAdjustment.objects.filter(period_start=period)
    if filters["status"]:
        records = records.filter(status=filters["status"])
        adjustments = adjustments.filter(status=filters["status"])
    else:
        records = records.exclude(status=PayrollWeek.Status.SUPERSEDED)
    for name in ("department", "team"):
        if filters[name]:
            records = records.filter(**{name: filters[name]})
            adjustments = adjustments.filter(**{name: filters[name]})
    if filters["employee"]:
        who = Q(employee_code__iexact=filters["employee"]) | Q(
            employee_name__icontains=filters["employee"]
        )
        records, adjustments = records.filter(who), adjustments.filter(who)
    records = list(records.order_by("employee_name", "week_start", "version"))
    _mark_settled_in(records)
    in_period = PayrollWeek.objects.filter(period_start=period)
    return {
        "filters": filters,
        "status_choices": STATUS_CHOICES,
        "departments": sorted(set(in_period.values_list("department", flat=True))),
        "teams": sorted(set(in_period.values_list("team", flat=True)) - {""}),
        "records": records,
        "adjustments": list(adjustments.order_by("employee_name", "week_start", "new_version")),
    }


@payroll_required
def payroll_period(request, period):
    """One pay period's register: the preview or the saved lines, who is still pending, and
    Finalize & export / downloads / Mark as paid (D-132–D-135)."""
    if period_start_for(period) != period:
        return redirect("payroll_period", period=period_start_for(period))
    now = timezone.now()
    if not period_ended(period, now):
        raise Http404("This pay period hasn't ended yet.")
    view = preview(period, now)
    rows, totals = table(view.lines)
    # No hours while OPEN (D-142) — except periods exported before registers existed, whose
    # week records are what was paid.
    show_records = view.state.status != "OPEN" or period in closed_periods()
    context = {
        "period": period,
        "state": view.state,
        "rows": rows,
        "totals": totals,
        "pending": view.pending,  # while OPEN: who still has to approve (D-142, D-143)
        "ready": view.state.status == READY,
        "show_records": show_records,
        **(_detail_tables(request, period) if show_records else {}),
        **_out_of_sync(),
    }
    return render(request, "payroll/period.html", context)


@require_POST
@payroll_required
def payroll_finalize(request, period):
    """Finalize & export: save the register and export it as one batch (D-135)."""
    try:
        register = finalize(period, actor=request.user.employee, now=timezone.now())
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(
            request, f"Register finalized and exported as batch {register.export_batch}."
        )
    return redirect("payroll_period", period=period)


@require_POST
@payroll_required
def payroll_register_paid(request, period):
    """Mark as paid: the register and its batch become PAID, once (D-135)."""
    get_object_or_404(PayrollRegister, period_start=period)
    paid = mark_paid(period, actor=request.user.employee, at=timezone.now())
    if paid is None:
        messages.info(request, "This register is already paid.")
    else:
        messages.success(request, "Register marked as paid.")
    return redirect("payroll_period", period=period)


@payroll_required
def payroll_register_csv(request, period):
    """The finalized register as CSV, as often as needed; never changes anything (D-135)."""
    register = get_object_or_404(PayrollRegister, period_start=period)
    return _csv(register_csv([register]), f"payroll-register_{file_stem(register)}.csv")


@payroll_required
def payroll_detail_csv(request, period):
    """The register's batch as the detailed WEEK / ADJUSTMENT CSV (D-123, D-135)."""
    register = get_object_or_404(PayrollRegister, period_start=period)
    return _csv(batches_csv(register.batches), f"payroll-detail_{file_stem(register)}.csv")


@payroll_required
def payroll_registers_csv(request):
    """Every finalized or paid register (optionally from / to a date) in one CSV (D-135)."""
    registers = PayrollRegister.objects.order_by("period_start")
    first, last = request.GET.get("from", ""), request.GET.get("to", "")
    if first:
        registers = registers.filter(period_start__gte=period_start_for(_date(first)))
    if last:
        registers = registers.filter(period_start__lte=_date(last))
    found = list(registers)
    if found:
        name = f"payroll-registers_{found[0].period_start}_to_{found[-1].period_end}.csv"
    else:
        name = "payroll-registers_none.csv"
    return _csv(register_csv(found, with_period=True), name)


@payroll_required
def payroll_batch_csv(request, batch):
    """Download an export batch as CSV again (older links); never changes any status."""
    if not (
        PayrollWeek.objects.filter(export_batch=batch).exists()
        or PayrollAdjustment.objects.filter(export_batch=batch).exists()
    ):
        raise Http404("No such batch.")
    return _csv(batches_csv([batch]), f"payroll-{batch}.csv")


def _pending_period(request, now):
    """?period= any date → its period (not a future one); default: the most recent ended."""
    value = request.GET.get("period")
    if not value:
        periods = ended_periods(now)
        return periods[0] if periods else current_period(now)
    period = period_start_for(_date(value))
    if period > current_period(now):
        raise Http404("Future pay periods have nothing to approve yet.")
    return period


@payroll_required
def payroll_pending(request):
    """Pending approvals by manager for payroll and HR: read only, nobody approves here
    (D-143)."""
    now = timezone.now()
    period = _pending_period(request, now)
    return render(
        request,
        "payroll/pending.html",
        {
            "report": pending_by_manager(period, now),
            "periods": ended_periods(now),
            "period": period,
            "period_end": period_end_for(period),
        },
    )


PENDING_COLUMNS = (
    "approver",
    "approver_team",
    "employee_code",
    "employee_name",
    "state",
    "overdue",
)


@payroll_required
def payroll_pending_csv(request):
    """The same list as CSV; every cell spreadsheet-safe (D-68, D-143)."""
    now = timezone.now()
    period = _pending_period(request, now)
    report = pending_by_manager(period, now)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(PENDING_COLUMNS)
    for group in report.open_groups:
        for row, state in group.pending:
            name = f"{row.employee.first_name} {row.employee.last_name}"
            values = [group.label, group.team, row.employee.employee_code, name, state]
            writer.writerow([safe_cell(v) for v in values] + ["yes" if report.overdue else "no"])
    name = f"payroll-pending_{period}_to_{period_end_for(period)}.csv"
    return _csv(out.getvalue(), name)


@payroll_required
def payroll_corrections(request):
    """Weeks that changed after they were exported or paid, with their adjustments (D-124)
    and the register each adjustment is paid in (D-138)."""
    return render(request, "payroll/corrections.html", {"corrections": corrections()})
