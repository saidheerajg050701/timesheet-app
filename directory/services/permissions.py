"""Who may see and do what (B.3, B.9 #6–#7, D-11, D-12, D-31).

Every function takes Employee records. Views call these on the server; hiding a menu item is
never the only protection (B.8).
"""

from functools import wraps

from django.core.exceptions import PermissionDenied

from directory.models import Employee


def manager_map():
    """{employee id: manager id} for everyone — one query (D-86)."""
    return dict(Employee.objects.values_list("pk", "manager_id"))


def reports_index(managers):
    """{manager id: [direct report ids]} from a manager_map()."""
    index = {}
    for pk, manager_id in managers.items():
        if manager_id is not None:
            index.setdefault(manager_id, []).append(pk)
    return index


def reporting_tree_ids(employee, managers=None):
    """Ids of everyone reporting to `employee`, directly or indirectly.

    Walks an in-memory map from one query (D-86). Cycle-safe: bad data such as A→B→A never
    loops, and nobody is ever part of their own tree.
    """
    index = reports_index(managers if managers is not None else manager_map())
    visited = {employee.pk}
    tree = set()
    frontier = [employee.pk]
    while frontier:
        reports = {r for pk in frontier for r in index.get(pk, ())} - visited
        visited |= reports
        tree |= reports
        frontier = list(reports)
    return tree


def team_scope(viewer, scope="tree"):
    """Ids the viewer's team page covers (D-81): never the viewer themselves.

    "tree" = whole reporting tree, or everyone for an admin; "direct" = direct reports only.
    The payroll flag adds nothing (D-12).
    """
    managers = manager_map()
    if scope == "direct":
        ids = {pk for pk, manager_id in managers.items() if manager_id == viewer.pk}
    elif viewer.is_admin:
        ids = set(managers)
    else:
        ids = reporting_tree_ids(viewer, managers)
    ids.discard(viewer.pk)
    return ids


def reporting_tree(employee):
    return Employee.objects.filter(pk__in=reporting_tree_ids(employee))


def is_manager(employee):
    """Manager is automatic: anyone with at least one report (B.3)."""
    return employee.reports.exists()


def can_view(viewer, target):
    """Own data, anyone in the viewer's reporting tree, or anyone for an admin.

    The payroll flag grants nothing here (D-12).
    """
    if viewer.pk == target.pk or viewer.is_admin:
        return True
    return target.pk in reporting_tree_ids(viewer)


def can_approve(viewer, target):
    """Direct manager; admins only for employees with no manager; never self (D-11)."""
    if viewer.pk == target.pk:
        return False
    if target.manager_id is not None:
        return target.manager_id == viewer.pk
    return viewer.is_admin


def can_edit(viewer, target):
    """Who may change the target's timesheets: the employee, or their approver (B.3).

    Status rules (draft, submitted, change request) are checked by the timesheet services.
    """
    return viewer.pk == target.pk or can_approve(viewer, target)


def can_access_payroll(employee):
    """Payroll pages: payroll flag or admin, and nothing more (D-12)."""
    return employee.is_payroll or employee.is_admin


def can_see_costs(employee):
    """Reports → Project budget (D-170): managers (their tree), payroll staff and admins
    (everyone). Someone who manages nobody and isn't payroll or admin: 403."""
    return employee.is_admin or employee.is_payroll or is_manager(employee)


def can_see_everyones_costs(employee):
    """Costs of every person (hours, rate used, cost): admins and payroll staff (D-170)."""
    return employee.is_admin or employee.is_payroll


def can_manage_pay(employee):
    """Pay records — salaries, pay types, history, the Pay CSV: admins only (D-167)."""
    return employee.is_admin


def can_access_team(employee):
    """Team analytics: managers (own tree) and admins (everyone) (D-31)."""
    return employee.is_admin or is_manager(employee)


def can_access_approvals(employee):
    """Approvals: managers and admins (admins approve employees with no manager, D-11/D-31)."""
    return employee.is_admin or is_manager(employee)


def menu_for(employee):
    manager = is_manager(employee)
    return {
        "team": employee.is_admin or manager,
        "approvals": employee.is_admin or manager,
        "payroll": can_access_payroll(employee),
        "admin": employee.is_admin,
        "reports": True,  # everyone: one's own hours at least (D-160)
        "costs": employee.is_admin or employee.is_payroll or manager,  # D-170
    }


# --- view helpers -----------------------------------------------------------------------


def ensure(allowed):
    """Raise 403 unless `allowed` is true. For object-level checks inside views."""
    if not allowed:
        raise PermissionDenied


def require(check):
    """Decorator for function views: 403 unless check(request.user.employee) is true."""

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            ensure(check(request.user.employee))
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


team_required = require(can_access_team)
approvals_required = require(can_access_approvals)
payroll_required = require(can_access_payroll)


class PermissionRequiredMixin:
    """For class-based views: set permission_check to one of the can_access_* functions."""

    permission_check = None

    def dispatch(self, request, *args, **kwargs):
        if self.permission_check is not None:
            ensure(type(self).permission_check(request.user.employee))
        return super().dispatch(request, *args, **kwargs)
