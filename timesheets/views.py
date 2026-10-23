from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from timesheets.forms import CATEGORY_GROUPS, day_choices, parse_entries, project_choices
from timesheets.models import ChangeRequest, Timesheet
from timesheets.services.approvals import approval_for_week
from timesheets.services.calendar import company_tz, week_start_for, week_state
from timesheets.services.changes import can_request_change, open_request_for, raise_request
from timesheets.services.summary import summarize
from timesheets.services.weeks import (
    STATUS_LABELS,
    EntryRow,
    WeekLocked,
    entry_rows,
    load_sheet,
    my_weeks,
    save_week,
)

BLANK_ROWS = 2  # empty rows offered under the existing ones; "Add row" adds more (D-35)


def placeholder(request, title, phase):
    """A page built in a later phase; its permission is already enforced (D-30)."""
    return render(request, "placeholder.html", {"title": title, "phase": phase})


def timesheet_list(request):
    """My weeks: status, hours, deadline, late and missed (FR-8)."""
    me = request.user.employee
    now = timezone.now()
    weeks = my_weeks(me, now)
    return render(
        request,
        "timesheets/list.html",
        {
            "weeks": weeks,
            "missed": sum(state.is_missed for state, _, _ in weeks),
            "current_week": week_start_for(now.astimezone(company_tz()).date()),
        },
    )


def _own_week(request, week):
    """The logged-in employee's Monday for `week`; future weeks don't open (D-33)."""
    monday = week_start_for(week)
    today = timezone.now().astimezone(company_tz()).date()
    if monday > week_start_for(today):
        raise Http404("Future weeks open on their Monday.")
    return request.user.employee, monday


def timesheet_week(request, week):
    """The week's entry rows: Save draft / Submit. Always the logged-in employee's own week."""
    if week_start_for(week) != week:
        return redirect("timesheet_week", week=week_start_for(week))
    me, monday = _own_week(request, week)
    now = timezone.now()
    state = week_state(me, monday, load_sheet(me, monday), now)
    rows, entries, errors = None, None, []
    if request.method == "POST":
        if not state.editable:
            raise WeekLocked("This week can't be changed.")
        submit = request.POST.get("action") == "submit"
        parsed = parse_entries(request.POST, monday)
        rows, entries, errors = parsed.rows, parsed.entries, parsed.errors
        if not errors:
            try:
                save_week(me, monday, parsed.entries, now=now, submit=submit)
            except ValidationError as exc:
                errors = exc.messages
            else:
                messages.success(request, "Week submitted." if submit else "Draft saved.")
                return redirect("timesheet_week", week=monday)
    context = _week_context(me, state, rows, entries, errors, now)
    return render(request, "timesheets/week.html", context)


def form_rows(sheet, posted_rows=None, *, editable=True):
    """Rows for the entry form, shared by the week page and Edit directly.

    After a failed save the rows are shown exactly as posted — no extra blank rows. A fresh
    page shows the saved rows plus BLANK_ROWS empty ones (day pre-filled; ignored if unused).
    """
    if posted_rows is not None:
        return posted_rows
    rows = entry_rows(sheet)
    if not editable:
        return rows
    start = max((r.index for r in rows), default=-1) + 1
    default_day = rows[-1].work_date if rows else ""
    return rows + [EntryRow(index=start + i, work_date=default_day) for i in range(BLANK_ROWS)]


def _week_context(me, state, rows, entries, errors, now):
    sheet = state.timesheet
    if rows is None:
        entries = list(sheet.entries.all()) if sheet else []
    rows = form_rows(sheet, rows, editable=state.editable)
    open_until = None
    if state.editable:
        reopened = sheet and sheet.status == Timesheet.Status.REOPENED
        open_until = sheet.reopen_until if reopened else state.deadline
    current_week = week_start_for(now.astimezone(company_tz()).date())
    return {
        "state": state,
        "status_label": STATUS_LABELS[state.status],
        "sheet": sheet,
        "rows": rows,
        "summary": summarize(entries, me, state.week_start),
        "summary_url": reverse("timesheet_totals", args=[state.week_start]),
        "change_request": open_request_for(sheet),
        "approval": approval_for_week(sheet),
        "can_request_change": can_request_change(state, now),
        "errors": errors,
        "open_until": open_until,
        "now": now,
        "previous_week": state.week_start - timedelta(weeks=1),
        "next_week": state.week_start + timedelta(weeks=1)
        if state.week_start < current_week
        else None,
        **_row_choices(state.week_start, rows),
    }


def _row_choices(week_start, rows=()):
    return {
        "day_choices": day_choices(week_start),
        "category_groups": CATEGORY_GROUPS,
        "project_choices": project_choices([r.project for r in rows if r.project.isdigit()]),
    }


@require_POST
def timesheet_totals(request, week):
    """HTMX: the day summary recomputed on the server from the rows as typed. Never saves."""
    me, monday = _own_week(request, week)
    entries = parse_entries(request.POST, monday).entries
    context = {
        "summary": summarize(entries, me, monday),
        "summary_url": request.path,
        "live": True,
    }
    return render(request, "timesheets/_summary.html", context)


@require_GET
def timesheet_row(request, week):
    """HTMX: one more empty row ("Add row"); no limit on the number of rows (D-35)."""
    _, monday = _own_week(request, week)
    try:
        index = int(request.GET.get("index", ""))
    except ValueError:
        raise Http404 from None
    day = request.GET.get("date", "")
    row = EntryRow(index=index, work_date=day if day in dict(day_choices(monday)) else "")
    context = {"row": row, "editable": True, **_row_choices(monday)}
    return render(request, "timesheets/_row.html", context)


@require_POST
def request_change(request, week):
    """The employee asks their manager to change a submitted, locked or approved week."""
    me, monday = _own_week(request, week)
    try:
        raise_request(me, monday, request.POST.get("reason", ""), now=timezone.now())
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, "Change requested. Your manager will see it in their inbox.")
    return redirect("timesheet_week", week=monday)


def request_list(request):
    """My change requests and how they were handled (FR-9)."""
    requests = (
        ChangeRequest.objects.filter(timesheet__employee=request.user.employee)
        .select_related("timesheet", "reviewer")
        .order_by("-created_at")
    )
    return render(request, "timesheets/my_requests.html", {"requests": requests})
