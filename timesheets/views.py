from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from timesheets.forms import CATEGORY_GROUPS, parse_entries, parse_grid_keys, project_choices
from timesheets.grid import build_grid
from timesheets.models import ChangeRequest, Project, TimeEntry, Timesheet
from timesheets.services.approvals import approval_for_week
from timesheets.services.calendar import company_tz, week_start_for, week_state
from timesheets.services.changes import can_request_change, open_request_for, raise_request
from timesheets.services.summary import summarize
from timesheets.services.weeks import (
    STATUS_LABELS,
    WeekLocked,
    entry_rows,
    load_sheet,
    my_weeks,
    save_week,
)


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
    """The logged-in employee's Sunday for `week`; future weeks don't open (D-33, D-111)."""
    week_start = week_start_for(week)
    today = timezone.now().astimezone(company_tz()).date()
    if week_start > week_start_for(today):
        raise Http404("Future weeks open on their Sunday.")
    return request.user.employee, week_start


def timesheet_week(request, week):
    """The week's entry rows: Save draft / Submit. Always the logged-in employee's own week."""
    if week_start_for(week) != week:
        return redirect("timesheet_week", week=week_start_for(week))
    me, week_start = _own_week(request, week)
    now = timezone.now()
    state = week_state(me, week_start, load_sheet(me, week_start), now)
    attempt = None
    if request.method == "POST":
        if not state.editable:
            raise WeekLocked("This week can't be changed.")
        submit = request.POST.get("action") == "submit"
        attempt = SaveAttempt(request.POST, week_start)
        if not attempt.errors:
            try:
                save_week(me, week_start, attempt.entries, now=now, submit=submit)
            except ValidationError as exc:
                attempt.rule_errors(exc.messages)
            else:
                messages.success(request, "Week submitted." if submit else "Draft saved.")
                return redirect("timesheet_week", week=week_start)
    context = _week_context(me, state, attempt, now)
    return render(request, "timesheets/week.html", context)


class SaveAttempt:
    """A posted week that didn't save: the grid is shown again exactly as posted (D-107),
    with each problem on its cell (D-108). Shared by the week page and Edit directly."""

    def __init__(self, post, week_start):
        self.week_start = week_start
        self.parsed = parse_entries(post, week_start)
        self.keys = parse_grid_keys(post)
        self.entries = self.parsed.entries
        self.errors = list(self.parsed.errors)
        self.messages = []

    def rule_errors(self, messages):
        self.errors = self.messages = list(messages)

    def grid(self):
        return build_grid(
            self.parsed.rows,
            self.week_start,
            editable=True,
            entries=self.entries,
            problems=self.parsed.problems,
            messages=self.messages,
            keys=self.keys,
        )


def week_grid(sheet, week_start, attempt=None, *, editable):
    """The grid for a saved week, or for a failed save (D-109)."""
    if attempt is not None:
        return attempt.grid()
    return build_grid(entry_rows(sheet), week_start, editable=editable)


def _week_context(me, state, attempt, now):
    sheet = state.timesheet
    entries = attempt.entries if attempt else list(sheet.entries.all()) if sheet else []
    grid = week_grid(sheet, state.week_start, attempt, editable=state.editable)
    open_until = None
    if state.editable:
        reopened = sheet and sheet.status == Timesheet.Status.REOPENED
        open_until = sheet.reopen_until if reopened else state.deadline
    current_week = week_start_for(now.astimezone(company_tz()).date())
    return {
        "state": state,
        "status_label": STATUS_LABELS[state.status],
        "sheet": sheet,
        "grid": grid,
        "summary": summarize(entries, me, state.week_start),
        "summary_url": reverse("timesheet_totals", args=[state.week_start]),
        "change_request": open_request_for(sheet),
        "approval": approval_for_week(sheet),
        "can_request_change": can_request_change(state, now),
        "errors": grid.errors,
        "open_until": open_until,
        "now": now,
        "previous_week": state.week_start - timedelta(weeks=1),
        "next_week": state.week_start + timedelta(weeks=1)
        if state.week_start < current_week
        else None,
        **grid_choices(state.week_start),
    }


def grid_choices(week_start):
    """What the editable grid's "+ Add row" dialog offers: categories, active projects (D-18)."""
    return {
        "row_url": reverse("timesheet_row", args=[week_start]),
        "category_groups": CATEGORY_GROUPS,
        "project_choices": project_choices(),
    }


@require_POST
def timesheet_totals(request, week):
    """HTMX: the day summary recomputed on the server from the rows as typed. Never saves."""
    me, week_start = _own_week(request, week)
    entries = parse_entries(request.POST, week_start).entries
    context = {
        "summary": summarize(entries, me, week_start),
        "summary_url": request.path,
        "live": True,
    }
    return render(request, "timesheets/_summary.html", context)


@require_GET
def timesheet_row(request, week):
    """HTMX: one empty grid row for "+ Add row" (D-107). Active projects only (D-18)."""
    _, week_start = _own_week(request, week)
    category = request.GET.get("category", "")
    project = request.GET.get("project", "")
    if category not in dict(TimeEntry.Category.choices):
        return HttpResponseBadRequest("Choose a category.")
    if category == TimeEntry.Category.PROJECT:
        if not (project.isdigit() and Project.objects.filter(pk=project, active=True).exists()):
            return HttpResponseBadRequest("Choose an active project.")
    else:
        project = ""
    grid = build_grid([], week_start, editable=True, keys=[(category, project)])
    return render(request, "timesheets/_grid_row.html", {"row": grid.rows[0], "grid": grid})


@require_POST
def request_change(request, week):
    """The employee asks their manager to change a submitted, locked or approved week."""
    me, week_start = _own_week(request, week)
    try:
        raise_request(me, week_start, request.POST.get("reason", ""), now=timezone.now())
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, "Change requested. Your manager will see it in their inbox.")
    return redirect("timesheet_week", week=week_start)


def request_list(request):
    """My change requests and how they were handled (FR-9)."""
    requests = (
        ChangeRequest.objects.filter(timesheet__employee=request.user.employee)
        .select_related("timesheet", "reviewer")
        .order_by("-created_at")
    )
    return render(request, "timesheets/my_requests.html", {"requests": requests})
