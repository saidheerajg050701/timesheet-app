"""Who may see pay and labour cost (D-167, D-170). Moved from directory/services/permissions.py
in Refactor R2 (D-174); still checked on the server for every page, filter and download."""

from apps.directory.services.permissions import is_manager


def can_see_costs(employee, *, manages=None):
    """Reports → Project budget (D-170): managers (their tree), payroll staff and admins
    (everyone). Someone who manages nobody and isn't payroll or admin: 403. `manages` is
    is_manager(employee) when the caller already knows it (the menu), saving a query."""
    if employee.is_admin or employee.is_payroll:
        return True
    return is_manager(employee) if manages is None else manages


def can_see_everyones_costs(employee):
    """Costs of every person (hours, rate used, cost): admins and payroll staff (D-170)."""
    return employee.is_admin or employee.is_payroll


def can_manage_pay(employee):
    """Pay records — salaries, pay types, history, the Pay CSV: admins only (D-167)."""
    return employee.is_admin
