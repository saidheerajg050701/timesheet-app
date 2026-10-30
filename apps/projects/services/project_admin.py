"""Admin changes to projects and tasks (D-88, D-148, D-149, D-155, D-168): audited saves,
the allowed-task list. Moved from directory_admin.py in Refactor R2 (D-174)."""

from django.db import transaction

from apps.audit.models import AuditLog
from apps.audit.services.log import record
from apps.directory.services.directory_admin import save_simple
from apps.projects.services.projects import assign_code
from apps.timesheets.models import TimeEntry


def save_project(actor, project):
    """Add or change a project; audited by its code (D-88). A new project gets the next I-code
    (D-155); the code never changes afterwards."""
    with transaction.atomic():
        if project.pk is None:
            assign_code(project)
        fields = ("code", "name", "active", "budget", "costs_from")  # budget: D-168
        return save_simple(actor, project, "Project", lambda p: p.code, fields)


def save_task(actor, task):
    """Add or change a task; audited by its code (D-148). The code is fixed once added."""
    fields = ("code", "name", "description", "active", "sort_order")
    return save_simple(actor, task, "Task", lambda t: t.code, fields)


def set_project_tasks(actor, project, tasks):
    """Set the tasks a project allows; one audited UPDATE when the list changes (D-149).

    Removing a task that saved entries use is allowed: history keeps it, and open weeks must
    choose another task when they are saved again. Returns {removed task: entries using it}.
    """
    with transaction.atomic():
        old = set(project.tasks.all())
        new = set(tasks)
        project.tasks.set(new)
        if old != new:
            record(
                AuditLog.Action.UPDATE,
                "Project",
                project.code,
                actor=actor,
                before={"tasks": sorted(t.code for t in old)},
                after={"tasks": sorted(t.code for t in new)},
            )
    removed = sorted(old - new, key=lambda t: (t.sort_order, t.code))
    in_use = {t: TimeEntry.objects.filter(project=project, task=t).count() for t in removed}
    return {t: n for t, n in in_use.items() if n}
