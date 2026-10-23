from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from directory.services.permissions import approvals_required
from timesheets.forms import kind_choices, parse_grid, row_totals
from timesheets.models import Timesheet
from timesheets.services.calendar import (
    company_tz,
    employed_on,
    week_days,
    week_start_for,
    week_state,
)
from timesheets.services.weeks import (
    STATUS_LABELS,
    GridRow,
    WeekLocked,
    grid_rows,
    load_sheet,
    my_weeks,
    save_week,
)

BLANK_ROWS = 2  # empty rows offered under the existing ones


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
            "missed": sum(state.is_missed for state, _ in weeks),
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
    """The weekly grid: Save draft / Submit. Always the logged-in employee's own week."""
    if week_start_for(week) != week:
        return redirect("timesheet_week", week=week_start_for(week))
    me, monday = _own_week(request, week)
    now = timezone.now()
    state = week_state(me, monday, load_sheet(me, monday), now)
    rows, errors = None, []
    if request.method == "POST":
        if not state.editable:
            raise WeekLocked("This week can't be changed.")
        submit = request.POST.get("action") == "submit"
        parsed = parse_grid(request.POST, monday)
        rows, errors = parsed.rows, parsed.errors
        if not errors:
            try:
                save_week(me, monday, parsed.entries, now=now, submit=submit)
            except ValidationError as exc:
                errors = exc.messages
            else:
                messages.success(request, "Week submitted." if submit else "Draft saved.")
                return redirect("timesheet_week", week=monday)
    return render(request, "timesheets/week.html", _week_context(me, state, rows, errors, now))


def _week_context(me, state, rows, errors, now):
    sheet = state.timesheet
    if rows is None:
        rows = grid_rows(sheet)
    if state.editable:
        start = max((r.index for r in rows), default=-1) + 1
        rows = rows + [GridRow(index=start + i, kind="", label="") for i in range(BLANK_ROWS)]
    per_day, week_total = row_totals(rows)
    open_until = None
    if state.editable:
        open_until = (
            sheet.reopen_until
            if sheet and sheet.status == Timesheet.Status.REOPENED
            else state.deadline
        )
    project_ids = [int(r.kind.split(":")[1]) for r in rows if r.kind.startswith("PROJECT:")]
    return {
        "state": state,
        "status_label": STATUS_LABELS[state.status],
        "sheet": sheet,
        "days": _days(me, state.week_start),
        "rows": rows,
        "kinds": kind_choices(project_ids),
        "errors": errors,
        "per_day": per_day,
        "week_total": week_total,
        "open_until": open_until,
        "now": now,
        "previous_week": state.week_start - timedelta(weeks=1),
        "next_week": state.week_start + timedelta(weeks=1)
        if state.week_start < week_start_for(now.astimezone(company_tz()).date())
        else None,
    }


def _days(employee, week_start):
    return [
        {"date": day, "weekend": day.weekday() >= 5, "employed": employed_on(employee, day)}
        for day in week_days(week_start)
    ]


@require_POST
def timesheet_totals(request, week):
    """HTMX: footer totals recomputed on the server from the grid as typed. Never saves."""
    me, monday = _own_week(request, week)
    per_day, week_total = row_totals(parse_grid(request.POST, monday).rows)
    return render(
        request,
        "timesheets/_totals.html",
        {
            "per_day": per_day,
            "week_total": week_total,
            "days": _days(me, monday),
            "state": week_state(me, monday, None, timezone.now()),
        },
    )


@require_GET
def timesheet_row(request, week):
    """HTMX: one more empty grid row ("Add row")."""
    me, monday = _own_week(request, week)
    try:
        index = int(request.GET.get("index", ""))
    except ValueError:
        raise Http404 from None
    return render(
        request,
        "timesheets/_row.html",
        {
            "row": GridRow(index=index, kind="", label=""),
            "days": _days(me, monday),
            "kinds": kind_choices(),
            "editable": True,
            "state": week_state(me, monday, None, timezone.now()),
        },
    )


def request_list(request):
    return placeholder(request, "Change requests", 6)


@approvals_required
def approval_list(request):
    return placeholder(request, "Approvals", 7)
