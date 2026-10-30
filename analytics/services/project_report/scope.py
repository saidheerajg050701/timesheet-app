"""Who is in the report and which People / Group by choices change it (D-160, D-165)."""

from django.core.exceptions import PermissionDenied

from analytics.services.project_report.constants import SCOPES
from directory.models import Employee
from directory.services.permissions import reporting_tree_ids


def scope_options(viewer, managers, everyone):
    """The People choices that change the result (D-165): whole tree / direct reports / one
    manager's group only when someone under the viewer manages people of their own (always
    for an admin with managers); otherwise none — the whole tree is the only answer."""
    leads = {m for m in managers.values() if m is not None}
    under = set(managers) if everyone else reporting_tree_ids(viewer, managers)
    return list(SCOPES) if (under - {viewer.pk}) & leads else []


def group_options(by_team, by_manager):
    """The Group by choices that change the result (D-165): Team when the people are in more
    than one team, Manager when By manager would have more than one row."""
    return [g for g, rows in (("team", by_team), ("manager", by_manager)) if len(rows) > 1]


def manages_anyone(viewer, managers, everyone):
    return everyone or any(m == viewer.pk for m in managers.values())


def report_people(viewer, filters, managers, everyone):
    """Ids of the people in the report: the viewer only (someone who manages nobody), or the
    viewer plus their tree / direct reports / one manager's group (everyone for an admin).
    A manager outside what the viewer may see is refused (403)."""
    if not manages_anyone(viewer, managers, everyone):
        return {viewer.pk}
    tree = set(managers) if everyone else reporting_tree_ids(viewer, managers)
    if filters.scope == "direct":
        return {viewer.pk} | {pk for pk, m in managers.items() if m == viewer.pk}
    if filters.scope == "manager":
        target = filters.manager
        if target.pk != viewer.pk and target.pk not in tree:
            raise PermissionDenied("Not allowed.")
        return {target.pk} | reporting_tree_ids(target, managers)
    return {viewer.pk} | tree


def manager_choices(viewer, managers, everyone):
    """The managers whose group the viewer may choose: everyone who manages someone in the
    viewer's tree (anyone for an admin), the viewer included. Sorted by name."""
    leads = {m for m in managers.values() if m is not None}
    visible = set(managers) if everyone else reporting_tree_ids(viewer, managers)
    ids = leads & (visible | {viewer.pk})
    return list(Employee.objects.filter(pk__in=ids).order_by("last_name", "first_name"))
