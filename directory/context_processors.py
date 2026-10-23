from directory.models import Employee
from directory.services.permissions import menu_for


def current_employee(request):
    """`me` (the logged-in employee, FR-4 header) and `menu` (what the navbar shows)."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    me = Employee.objects.select_related("team", "manager").get(pk=user.employee_id)
    return {"me": me, "menu": menu_for(me)}
