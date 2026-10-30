"""The report's fixed number of database reads (D-164), then build_report."""

from apps.directory.models import Employee
from apps.directory.services.permissions import manager_map
from apps.projects.models import Project, Task
from apps.reports.services.project_report.aggregate import build_report
from apps.reports.services.project_report.filters import read_filters
from apps.reports.services.project_report.scope import (
    group_options,
    manager_choices,
    manages_anyone,
    report_people,
    scope_options,
)
from apps.timesheets.models import TimeEntry


def project_report(viewer, params, now, *, everyone=None):
    """The report for `viewer` from URL parameters (D-160–D-164). `everyone` (default: the
    viewer is an admin) makes the viewer see everyone, as payroll staff do on Project budget."""
    managers = manager_map()
    # Who counts as seeing everyone: admins; for Project budget also payroll staff (D-170).
    everyone = viewer.is_admin if everyone is None else everyone
    managing = manages_anyone(viewer, managers, everyone)
    scopes = scope_options(viewer, managers, everyone) if managing else []
    filters = read_filters(params, viewer, now, managing, scopes)
    ids = report_people(viewer, filters, managers, everyone)
    candidates = list(
        Employee.objects.filter(pk__in=ids)
        .select_related("team", "manager")
        .order_by("last_name", "first_name", "employee_code")
    )
    projects = Project.objects.in_bulk()
    tasks = Task.objects.in_bulk()
    entries = (
        TimeEntry.objects.filter(
            timesheet__employee_id__in=ids, work_date__range=(filters.start, filters.end)
        )
        .exclude(category=TimeEntry.Category.BREAK)
        .order_by(  # the Detail: by date, then person, then time
            "work_date",
            "timesheet__employee__last_name",
            "timesheet__employee__first_name",
            "timesheet__employee__employee_code",
            "start_time",
            "pk",
        )
        .values_list(
            "timesheet_id",
            "timesheet__employee_id",
            "timesheet__week_start",
            "timesheet__status",
            "timesheet__reopen_until",
            "work_date",
            "category",
            "project_id",
            "task_id",
            "minutes",
        )
    )
    report = build_report(
        viewer, filters, managing, managers, candidates, entries, projects, tasks, now
    )
    report.managers = managers
    if managing:
        report.manager_choices = manager_choices(viewer, managers, everyone)
        filters.groups = group_options(report.by_team, report.by_manager)
        if filters.group not in filters.groups:  # not offered: the one that applies, or none
            filters.group = filters.groups[0] if filters.groups else ""
    return report
