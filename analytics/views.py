from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from analytics.services.metrics import RANGES, dashboard_for, range_weeks
from directory.models import Employee
from directory.services.permissions import can_view, ensure, team_required
from timesheets.views import placeholder


@team_required
def team(request):
    return placeholder(request, "Team", 10)


@team_required
def team_member(request, employee_code):
    target = get_object_or_404(Employee, employee_code=employee_code)
    ensure(can_view(request.user.employee, target))  # managers: own tree only; admins: all
    return placeholder(request, f"Team — {target.first_name} {target.last_name}", 10)


def dashboard(request):
    """FR-5: the logged-in person's own dashboard. No parameter can pick another employee."""
    weeks = range_weeks(request.GET.get("weeks"))
    dash = dashboard_for(request.user.employee, weeks, timezone.now())
    return render(request, "analytics/dashboard.html", {"dash": dash, "ranges": RANGES})
