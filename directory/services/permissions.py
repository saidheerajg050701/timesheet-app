"""Who may see and do what (B.3, B.9 #6–#7, D-11, D-12, D-31).

Every function takes Employee records. Views call these on the server; hiding a menu item is
never the only protection (B.8).
"""

from functools import wraps

from django.core.exceptions import PermissionDenied

from directory.models import Employee


def reporting_tree_ids(employee):
    """Ids of everyone reporting to `employee`, directly or indirectly.

    One query per level. Cycle-safe: bad data such as A→B→A never loops, and nobody is
    ever part of their own tree.
    """
    visited = {employee.pk}
    tree = set()
    frontier = {employee.pk}
    while frontier:
        reports = set(Employee.objects.filter(manager_id__in=frontier).values_list("pk", flat=True))
        frontier = reports - visited
        visited |= frontier
        tree |= frontier
    return tree


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
