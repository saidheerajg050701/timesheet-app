from django.shortcuts import get_object_or_404

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
