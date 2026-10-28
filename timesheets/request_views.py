"""The handler's side of change requests: inbox, detail, Reject / Unlock / Edit directly (FR-9).

Every view checks on the server that the user may handle the request (can_approve, D-47).
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from directory.services.permissions import approvals_required, can_approve, ensure
from timesheets.forms import parse_entries
from timesheets.models import ChangeRequest
from timesheets.services.changes import (
    edit_directly,
    handled_by,
    reject_request,
    unlock_request,
)
from timesheets.services.summary import summarize
from timesheets.views import (
    SaveAttempt,
    editor_urls,
    grid_choices,
    project_list,
    row_action,
    week_grid,
)

RECENT = 20


@approvals_required
def request_inbox(request):
    """Open requests first, then the most recently handled ones."""
    mine = handled_by(request.user.employee)
    return render(
        request,
        "timesheets/request_inbox.html",
        {
            "open_requests": mine.filter(status=ChangeRequest.Status.OPEN).order_by("created_at"),
            "recent": mine.exclude(status=ChangeRequest.Status.OPEN).order_by("-resolved_at")[
                :RECENT
            ],
        },
    )


def _handleable(request, pk, *, open_only=False):
    change = get_object_or_404(
        ChangeRequest.objects.select_related("timesheet__employee", "requester", "reviewer"),
        pk=pk,
    )
    ensure(can_approve(request.user.employee, change.timesheet.employee))  # never own (D-11)
    if open_only:
        ensure(change.status == ChangeRequest.Status.OPEN)
    return change


def request_detail(request, pk):
    """The request, the week as it is now, and the Reject / Unlock actions."""
    change = _handleable(request, pk)
    if request.method == "POST":
        action = request.POST.get("action")
        note = request.POST.get("note", "")
        handlers = {"reject": reject_request, "unlock": unlock_request}
        if action not in handlers:
            return redirect("request_detail", pk=change.pk)
        handlers[action](change, request.user.employee, note, now=timezone.now())
        done = "rejected" if action == "reject" else "unlocked for the employee"
        messages.success(request, f"Request {done}.")
        return redirect("request_inbox")
    sheet = change.timesheet
    return render(
        request,
        "timesheets/request_detail.html",
        {
            "change": change,
            "sheet": sheet,
            "grid": week_grid(sheet, sheet.week_start, editable=False),
            "summary": summarize(list(sheet.entries.all()), sheet.employee, sheet.week_start),
        },
    )


def request_edit(request, pk):
    """Edit directly: the employee's rows with the same checks as their own page (D-49)."""
    change = _handleable(request, pk, open_only=True)
    sheet = change.timesheet
    attempt = None
    if request.method == "POST":
        attempt = SaveAttempt(request.POST, sheet.week_start)
        if not attempt.errors:
            note = request.POST.get("note", "")
            try:
                edit_directly(
                    change, request.user.employee, attempt.entries, note, now=timezone.now()
                )
            except ValidationError as exc:
                attempt.rule_errors(exc.messages)
            else:
                messages.success(request, "Week edited and submitted on the employee's behalf.")
                return redirect("request_inbox")
    entries = attempt.entries if attempt else list(sheet.entries.all())
    grid = week_grid(sheet, sheet.week_start, attempt, editable=True)
    return render(
        request,
        "timesheets/request_edit.html",
        {
            "change": change,
            "sheet": sheet,
            "grid": grid,
            "errors": grid.errors,
            "summary": summarize(entries, sheet.employee, sheet.week_start),
            "summary_url": reverse("request_totals", args=[change.pk]),
            **grid_choices(sheet.week_start, editor_urls("request", change.pk)),
        },
    )


@require_POST
def request_rows(request, pk):
    """HTMX: Edit directly's row actions (D-129); saved and audited with the week (D-49)."""
    change = _handleable(request, pk, open_only=True)
    return row_action(request, change.timesheet.week_start, editor_urls("request", change.pk))


@require_GET
def request_projects(request, pk):
    """HTMX: Edit directly's project search — the employee's recent projects (D-157, D-158)."""
    change = _handleable(request, pk, open_only=True)
    sheet = change.timesheet
    return project_list(request, sheet.employee, sheet.week_start)


@require_POST
def request_totals(request, pk):
    """HTMX: day summary for the employee's week as the handler types. Never saves."""
    change = _handleable(request, pk, open_only=True)
    sheet = change.timesheet
    entries = parse_entries(request.POST, sheet.week_start).entries
    context = {
        "summary": summarize(entries, sheet.employee, sheet.week_start),
        "summary_url": request.path,
        "live": True,
    }
    return render(request, "timesheets/_summary.html", context)
