"""Tasks and charge codes (Change 10, D-148–D-151): the one place for what a task means.

A charge code is "<project code>-<task code>", e.g. I-001-DEV. It is worked out, never
stored. Project work saved before tasks existed has no task: "Task not recorded".
"""

from timesheets.models import Project, Task

TASK_NOT_RECORDED = "Task not recorded"


def charge_code(project, task):
    """ "I-001-DEV"; just the project code when the entry has no task (history)."""
    return f"{project.code}-{task.code}" if task is not None else project.code


def task_label(task):
    """ "DEV Development", or "Task not recorded"."""
    return f"{task.code} {task.name}" if task is not None else TASK_NOT_RECORDED


def task_problem(project, task):
    """Why project work on `project` can't be booked to `task`, or "" (D-151)."""
    if task is None:
        return f"project work needs a task — choose one for {project.code}."
    if not task.active:
        return f"task {task.code} is no longer active."
    if not project.tasks.filter(pk=task.pk).exists():
        return f"task {task.code} is not allowed for project {project.code}."
    return ""


def task_choices():
    """{project id: [[task code, "DEV Development"], …]} for every active project — what the
    grid's "+ Add row" and ⋮ dialogs offer once a project is chosen (D-152)."""
    choices = {}
    projects = Project.objects.filter(active=True).prefetch_related("tasks")
    for project in projects:
        tasks = [t for t in project.tasks.all() if t.active]  # Task.Meta: by sort order
        choices[str(project.pk)] = [[t.code, task_label(t)] for t in tasks]
    return choices


def active_tasks():
    return Task.objects.filter(active=True)
