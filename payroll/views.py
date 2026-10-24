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
from payroll.models import PayrollWeek
from payroll.services.export import (
    batch_csv,
    batches_for,
    corrections,
    employee_totals,
    export_period,
    mark_paid,
)
from payroll.services.publish import out_of_sync
from timesheets.services.calendar import default_period, period_start_for

STATUS_CHOICES = [("", "All but superseded")] + list(PayrollWeek.Status.choices)


def _periods():
    return list(
        PayrollWeek.objects.order_by("-period_start")
        .values_list("period_start", flat=True)
        .distinct()
    )


def _chosen_period(value, periods):
    if value:
        try:
            return period_start_for(date.fromisoformat(value))
        except ValueError:
            raise Http404("Not a date.") from None
    return periods[0] if periods else default_period(timezone.now())


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
            "totals": employee_totals(records),
            "records": records,
            "batches": batches_for(period),
            "exportable": in_period.filter(status=PayrollWeek.Status.CURRENT).count(),
            "missing": missing,
            "stale": stale,
        },
    )


@require_POST
@payroll_required
def payroll_export(request):
    """Stamp a new batch for all CURRENT records of the period, then download it (D-68)."""
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
    if not PayrollWeek.objects.filter(export_batch=batch).exists():
        raise Http404("No such batch.")
    response = HttpResponse("﻿" + batch_csv(batch), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="payroll-{batch}.csv"'
    return response


@require_POST
@payroll_required
def payroll_mark_paid(request, batch):
    """EXPORTED records of the batch become PAID (D-69)."""
    count = mark_paid(batch, actor=request.user.employee, at=timezone.now())
    if count:
        messages.success(request, f"Batch {batch}: {count} week record(s) marked as paid.")
    else:
        messages.info(request, f"Batch {batch} has nothing left to mark as paid.")
    period = PayrollWeek.objects.filter(export_batch=batch).values_list("period_start", flat=True)
    target = reverse("payroll") + (f"?period={period[0].isoformat()}" if period else "")
    return redirect(target)


@payroll_required
def payroll_corrections(request):
    """Weeks that changed after they were exported or paid (D-70)."""
    return render(request, "payroll/corrections.html", {"corrections": corrections()})
