"""Biweekly approvals pages (FR-7). Thin: the rules live in timesheets/services/approvals.py."""

from datetime import date, timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from directory.models import Employee
from directory.services.permissions import approvals_required
from timesheets.services.approvals import (
    approve_period,
    bulk_approve,
    period_row,
    period_rows,
    reject_period,
)
from timesheets.services.calendar import (
    current_period,
    default_period,
    period_start_for,
    recent_periods,
)
from timesheets.services.changes import unlock_from_approvals
from timesheets.views import week_grid


def _period_from(value, now):
    """?period= any date → its period start; default = most recent completed (D-54)."""
    if not value:
        return default_period(now)
    try:
        period = period_start_for(date.fromisoformat(value))
    except ValueError:
        raise Http404("Not a date.") from None
    if period > current_period(now):
        raise Http404("Future pay periods can't be approved yet.")
    return period


def _list_url(period):
    return f"{reverse('approvals')}?period={period.isoformat()}"


@approvals_required
def approval_list(request):
    now = timezone.now()
    period = _period_from(request.GET.get("period"), now)
    rows = period_rows(request.user.employee, period, now)
    current = current_period(now)
    return render(
        request,
        "timesheets/approvals.html",
        {
            "period": period,
            "period_end": period + timedelta(days=13),
            "periods": recent_periods(now),
            "previous": period - timedelta(weeks=2),
            "next": period + timedelta(weeks=2) if period < current else None,
            "rows": rows,
            "bulk_count": sum(row.can_bulk for row in rows),
        },
    )


@approvals_required
def approval_detail(request, period, employee_code):
    now = timezone.now()
    if period_start_for(period) != period:
        return redirect(
            "approval_detail", period=period_start_for(period), employee_code=employee_code
        )
    if period > current_period(now):
        raise Http404("Future pay periods can't be approved yet.")
    employee = get_object_or_404(Employee, employee_code=employee_code)
    me = request.user.employee
    row = period_row(me, employee, period, now)  # 403 unless me approves this employee (D-11)
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "approve":
                approve_period(me, employee, period, now=now)
                messages.success(request, f"Approved {employee.first_name}'s period.")
                return redirect(_list_url(period))
            if action == "reject":
                reject_period(me, employee, period, request.POST.get("comment", ""), now=now)
                messages.success(request, f"Rejected — {employee.first_name} can fix and resubmit.")
                return redirect(_list_url(period))
            if action == "unlock":
                week = date.fromisoformat(request.POST.get("week", ""))
                unlock_from_approvals(me, employee, week, now=now)
                messages.success(
                    request, f"Week of {week:%b %-d} unlocked for {employee.first_name}."
                )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        except ValueError:
            raise Http404("Unknown week.") from None
        return redirect("approval_detail", period=period, employee_code=employee_code)
    return render(
        request,
        "timesheets/approval_detail.html",
        {
            "row": row,
            "weeks": [
                (
                    week,
                    week_grid(week.sheet, week.week_start, editable=False),
                    f"entries-week-{week.number}",  # two grids on one page
                )
                for week in row.weeks
            ],
        },
    )


@require_POST
@approvals_required
def approval_bulk(request):
    """Approve every ticked clean row; each in its own transaction (D-63)."""
    now = timezone.now()
    period = _period_from(request.POST.get("period"), now)
    approved, skipped = bulk_approve(
        request.user.employee, period, request.POST.getlist("employee"), now=now
    )
    if approved:
        messages.success(request, f"Approved {len(approved)}: {', '.join(approved)}.")
    for name, reason in skipped:
        messages.warning(request, f"Skipped {name}: {reason}")
    if not approved and not skipped:
        messages.info(request, "Nothing was selected.")
    return redirect(_list_url(period))
