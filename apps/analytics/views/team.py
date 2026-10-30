"""Team (FR-6, D-81–D-86): the people under the viewer and read-only drill-downs (D-85)."""

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.analytics.services.metrics import RANGES, dashboard_for, range_weeks
from apps.analytics.services.team import SORT_KEYS, team_dashboard
from apps.directory.models import Employee
from apps.directory.services.permissions import can_view, ensure, team_required
from apps.timesheets.services.calendar import company_tz, week_start_for, week_state
from apps.timesheets.services.summary import summarize
from apps.timesheets.services.weeks import load_sheet, my_weeks
from apps.timesheets.views.weeks import week_grid


@team_required
def team(request):
    """FR-6: the people under the viewer (D-81–D-84). Every person comes from team_scope."""
    try:
        team_id = int(request.GET.get("team", "")) or None
    except ValueError:
        team_id = None
    board = team_dashboard(
        request.user.employee,
        scope=request.GET.get("scope", "tree"),
        team_id=team_id,
        weeks=range_weeks(request.GET.get("weeks")),
        sort=request.GET.get("sort", "name"),
        direction=request.GET.get("dir", "asc"),
        now=timezone.now(),
    )
    return render(
        request,
        "analytics/team.html",
        {"board": board, "ranges": RANGES, "sort_urls": _sort_urls(request, board)},
    )


def _sort_urls(request, board):
    """Header links: same filters, this column; clicking the sorted column flips direction."""
    urls = {}
    for column in SORT_KEYS:
        query = request.GET.copy()
        query["sort"] = column
        flip = board.sort == column and board.direction == "asc"
        query["dir"] = "desc" if flip else "asc"
        urls[column] = f"?{query.urlencode()}"
    return urls


def _visible_member(request, employee_code):
    """A person the viewer may see (can_view on every drill-down, D-85); 404 if unknown."""
    target = get_object_or_404(
        Employee.objects.select_related("team", "manager"), employee_code=employee_code
    )
    ensure(can_view(request.user.employee, target))  # managers: own tree; admins: everyone
    return target


@team_required
def team_member(request, employee_code):
    """Read-only view of one person's dashboard and timesheets (D-85)."""
    target = _visible_member(request, employee_code)
    weeks = range_weeks(request.GET.get("weeks"))
    now = timezone.now()
    return render(
        request,
        "analytics/team_member.html",
        {
            "target": target,
            "dash": dashboard_for(target, weeks, now),
            "timesheets": my_weeks(target, now, count=weeks),
            "ranges": RANGES,
        },
    )


@team_required
def team_member_week(request, employee_code, week):
    """One of their weeks, read-only: rows, day summary, status (D-85)."""
    target = _visible_member(request, employee_code)
    if week_start_for(week) != week:
        return redirect("team_member_week", employee_code=employee_code, week=week_start_for(week))
    now = timezone.now()
    if week > week_start_for(now.astimezone(company_tz()).date()):
        raise Http404("Future weeks have no timesheet yet.")
    sheet = load_sheet(target, week)
    return render(
        request,
        "analytics/team_week.html",
        {
            "target": target,
            "state": week_state(target, week, sheet, now),
            "grid": week_grid(sheet, week, editable=False),
            "summary": summarize(list(sheet.entries.all()) if sheet else [], target, week),
        },
    )
