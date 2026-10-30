"""Biweekly approvals pages (FR-7). Thin: the rules live in timesheets/services/approvals.py."""

from datetime import date, timedelta

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from directory.models import Employee
from directory.services.permissions import approvals_required
from timesheets.forms import parse_entries
from timesheets.services.approvals import (
    approve_period,
    bulk_approve,
    edit_blockers,
    period_row,
    period_rows,
    reject_period,
    unsubmitted_notes,
)
from timesheets.services.calendar import (
    approval_deadline_for,
    current_period,
    default_period,
    period_start_for,
    recent_periods,
)
from timesheets.services.changes import (
    approval_week,
    edit_for_approval,
    unlock_from_approvals,
)
from timesheets.services.summary import summarize
from timesheets.views.weeks import (
    SaveAttempt,
    editor_urls,
    grid_choices,
    project_list,
    row_action,
    week_grid,
)


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
    deadline = approval_deadline_for(period)
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
            "deadline": deadline,
            "overdue": now >= deadline,  # unapproved rows are Overdue after it (D-133)
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
                confirmed = request.POST.get("confirm_unsubmitted") == "1"
                approve_period(me, employee, period, now=now, confirm_unsubmitted=confirmed)
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
                    not edit_blockers(row, week),  # the approver may edit it (D-140)
                )
                for week in row.weeks
            ],
            "unsubmitted_notes": unsubmitted_notes(row),
        },
    )


def _approval_week(request, period, employee_code, week):
    """(employee, row, week view) for a week of `period`; 404 for any other week, 403 unless
    the viewer approves the employee (D-11)."""
    if week not in (period, period + timedelta(weeks=1)) or period_start_for(period) != period:
        raise Http404("Not a week of this pay period.")
    employee = get_object_or_404(Employee, employee_code=employee_code)
    row, view = approval_week(request.user.employee, employee, week, timezone.now())
    return employee, row, view


@approvals_required
def approval_week_edit(request, period, employee_code, week):
    """The approver edits a SUBMITTED or LOCKED week in the weekly grid (D-140)."""
    employee, row, view = _approval_week(request, period, employee_code, week)
    detail = reverse("approval_detail", args=[period, employee_code])
    problems = edit_blockers(row, view)
    if problems:
        messages.error(request, " ".join(problems))
        return redirect(detail)
    attempt = None
    if request.method == "POST":
        attempt = SaveAttempt(request.POST, week)
        if not attempt.errors:
            try:
                edit_for_approval(
                    request.user.employee, employee, week, attempt.entries, now=timezone.now()
                )
            except ValidationError as exc:
                attempt.rule_errors(exc.messages)
            else:
                messages.success(request, f"Week of {week:%b %-d} saved for {employee.first_name}.")
                return redirect(detail)
    sheet = view.sheet
    entries = attempt.entries if attempt else list(sheet.entries.all()) if sheet else []
    grid = week_grid(sheet, week, attempt, editable=True)
    summary_url = reverse("approval_week_totals", args=[period, employee_code, week])
    return render(
        request,
        "timesheets/approval_edit.html",
        {
            "row": row,
            "week": view,
            "grid": grid,
            "errors": grid.errors,
            "summary": summarize(entries, employee, week),
            "summary_url": summary_url,
            "detail_url": detail,
            **grid_choices(week, editor_urls("approval_week", period, employee_code, week)),
        },
    )


def _editable(request, period, employee_code, week):
    employee, row, view = _approval_week(request, period, employee_code, week)
    if edit_blockers(row, view):
        raise PermissionDenied("This week can't be edited from Approvals now.")
    return employee


@require_POST
@approvals_required
def approval_week_rows(request, period, employee_code, week):
    """HTMX: the edit grid's row actions (D-129); saved with the week (D-140)."""
    _editable(request, period, employee_code, week)
    urls = editor_urls("approval_week", period, employee_code, week)
    return row_action(request, week, urls)


@require_GET
@approvals_required
def approval_week_projects(request, period, employee_code, week):
    """HTMX: the Approvals edit's project search — the employee's recent projects (D-157)."""
    employee = _editable(request, period, employee_code, week)
    return project_list(request, employee, week)


@require_POST
@approvals_required
def approval_week_totals(request, period, employee_code, week):
    """HTMX: the day summary as the approver types. Never saves."""
    employee = _editable(request, period, employee_code, week)
    context = {
        "summary": summarize(parse_entries(request.POST, week).entries, employee, week),
        "summary_url": request.path,
        "live": True,
    }
    return render(request, "timesheets/_summary.html", context)


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
