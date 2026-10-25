"""Payroll pages (FR-11): payroll staff and admins only (D-12). Only approved hours are shown —
never timesheet rows, notes or reasons."""

from datetime import date

from django.contrib import messages
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from directory.services.permissions import payroll_required
from payroll.models import PayrollAdjustment, PayrollWeek
from payroll.services.export import (
    batch_csv,
    batches_for,
    corrections,
    employee_totals,
    export_period,
    exportable,
    mark_paid_counts,
)
from payroll.services.publish import out_of_sync
from timesheets.services.calendar import default_period, period_start_for

STATUS_CHOICES = [("", "All but superseded")] + list(PayrollWeek.Status.choices)


def _periods():
    """Periods with week records or adjustments carried to them (D-124), newest first."""
    weeks = PayrollWeek.objects.values_list("period_start", flat=True).distinct()
    adjustments = PayrollAdjustment.objects.values_list("period_start", flat=True).distinct()
    return sorted({*weeks, *adjustments}, reverse=True)


def _chosen_period(value, periods):
    if value:
        try:
            return period_start_for(date.fromisoformat(value))
        except ValueError:
            raise Http404("Not a date.") from None
    return periods[0] if periods else default_period(timezone.now())


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


@payroll_required
def payroll_home(request):
    periods = _periods()
    period = _chosen_period(request.GET.get("period"), periods)
    filters = {
        key: request.GET.get(key, "").strip()
        for key in ("department", "team", "employee", "status")
    }
    records = PayrollWeek.objects.filter(period_start=period)
    if filters["status"]:
        records = records.filter(status=filters["status"])
    else:
        records = records.exclude(status=PayrollWeek.Status.SUPERSEDED)
    if filters["department"]:
        records = records.filter(department=filters["department"])
    if filters["team"]:
        records = records.filter(team=filters["team"])
    if filters["employee"]:
        records = records.filter(
            Q(employee_code__iexact=filters["employee"])
            | Q(employee_name__icontains=filters["employee"])
        )
    records = list(records.order_by("employee_name", "week_start", "version"))
    _mark_settled_in(records)
    adjustments = PayrollAdjustment.objects.filter(period_start=period)
    if filters["status"]:
        adjustments = adjustments.filter(status=filters["status"])
    if filters["department"]:
        adjustments = adjustments.filter(department=filters["department"])
    if filters["team"]:
        adjustments = adjustments.filter(team=filters["team"])
    if filters["employee"]:
        adjustments = adjustments.filter(
            Q(employee_code__iexact=filters["employee"])
            | Q(employee_name__icontains=filters["employee"])
        )
    adjustments = list(adjustments.order_by("employee_name", "week_start", "new_version"))
    new_weeks, new_adjustments = exportable(period)
    in_period = PayrollWeek.objects.filter(period_start=period)
    missing, stale = out_of_sync()
    return render(
        request,
        "payroll/home.html",
        {
            "period": period,
            "periods": periods,
            "filters": filters,
            "status_choices": STATUS_CHOICES,
            "departments": sorted(set(in_period.values_list("department", flat=True))),
            "teams": sorted(set(in_period.values_list("team", flat=True)) - {""}),
            "totals": employee_totals(records, adjustments),
            "records": records,
            "adjustments": adjustments,
            "batches": batches_for(period),
            "exportable": len(new_weeks) + len(new_adjustments),
            "exportable_weeks": len(new_weeks),
            "exportable_adjustments": len(new_adjustments),
            "missing": missing,
            "stale": stale,
        },
    )


@require_POST
@payroll_required
def payroll_export(request):
    """Stamp a new batch for the period's CURRENT records and adjustments, then download it
    (D-68, D-123)."""
    period = _chosen_period(request.POST.get("period"), _periods())
    batch = export_period(period, actor=request.user.employee, at=timezone.now())
    if batch is None:
        messages.info(request, "Nothing new to export for this period.")
        return redirect(f"{reverse('payroll')}?period={period.isoformat()}")
    messages.success(request, f"Exported batch {batch}.")
    return redirect("payroll_batch_csv", batch=batch)


@payroll_required
def payroll_batch_csv(request, batch):
    """Download (or download again) a batch as CSV; never changes any status."""
    if not (
        PayrollWeek.objects.filter(export_batch=batch).exists()
        or PayrollAdjustment.objects.filter(export_batch=batch).exists()
    ):
        raise Http404("No such batch.")
    response = HttpResponse("﻿" + batch_csv(batch), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="payroll-{batch}.csv"'
    return response


@require_POST
@payroll_required
def payroll_mark_paid(request, batch):
    """EXPORTED records and adjustments of the batch become PAID (D-69, D-123)."""
    weeks, adjustments = mark_paid_counts(batch, actor=request.user.employee, at=timezone.now())
    if weeks or adjustments:
        extra = f" and {adjustments} adjustment(s)" if adjustments else ""
        messages.success(request, f"Batch {batch}: {weeks} week record(s){extra} marked as paid.")
    else:
        messages.info(request, f"Batch {batch} has nothing left to mark as paid.")
    period = [
        *PayrollWeek.objects.filter(export_batch=batch).values_list("period_start", flat=True),
        *PayrollAdjustment.objects.filter(export_batch=batch).values_list(
            "period_start", flat=True
        ),
    ]
    target = reverse("payroll") + (f"?period={period[0].isoformat()}" if period else "")
    return redirect(target)


@payroll_required
def payroll_corrections(request):
    """Weeks that changed after they were exported or paid, with their adjustments (D-124)."""
    return render(request, "payroll/corrections.html", {"corrections": corrections()})
