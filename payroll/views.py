from directory.services.permissions import payroll_required
from timesheets.views import placeholder


@payroll_required
def payroll_home(request):
    return placeholder(request, "Payroll", 8)
