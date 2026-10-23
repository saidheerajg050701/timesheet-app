"""The handler's side of change requests: inbox, detail, Reject / Unlock / Edit directly (FR-9).

Every view checks on the server that the user may handle the request (can_approve, D-47).
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

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
from timesheets.services.weeks import entry_rows
from timesheets.views import _row_choices, form_rows

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
            "rows": entry_rows(sheet),
            "summary": summarize(list(sheet.entries.all()), sheet.employee, sheet.week_start),
        },
    )


def request_edit(request, pk):
    """Edit directly: the employee's rows with the same checks as their own page (D-49)."""
    change = _handleable(request, pk, open_only=True)
    sheet = change.timesheet
    rows, entries, errors = None, None, []
    if request.method == "POST":
        parsed = parse_entries(request.POST, sheet.week_start)
        rows, entries, errors = parsed.rows, parsed.entries, parsed.errors
        if not errors:
            note = request.POST.get("note", "")
            try:
                edit_directly(change, request.user.employee, entries, note, now=timezone.now())
            except ValidationError as exc:
                errors = exc.messages
            else:
                messages.success(request, "Week edited and submitted on the employee's behalf.")
                return redirect("request_inbox")
    if rows is None:
        entries = list(sheet.entries.all())
    rows = form_rows(sheet, rows)
    return render(
        request,
        "timesheets/request_edit.html",
        {
            "change": change,
            "sheet": sheet,
            "rows": rows,
            "errors": errors,
            "summary": summarize(entries, sheet.employee, sheet.week_start),
            "summary_url": reverse("request_totals", args=[change.pk]),
            **_row_choices(sheet.week_start, rows),
        },
    )


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
