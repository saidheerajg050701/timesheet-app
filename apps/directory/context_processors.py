from apps.directory.models import Employee
from apps.directory.services.permissions import menu_for


def current_employee(request):
    """`me` (the logged-in employee, FR-4 header) and `menu` (navbar items, open requests)."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    me = Employee.objects.select_related("team", "manager").get(pk=user.employee_id)
    menu = menu_for(me)
    if menu["approvals"]:
        from apps.timesheets.services.changes import open_request_count

        menu["open_requests"] = open_request_count(me)
    return {"me": me, "menu": menu}
