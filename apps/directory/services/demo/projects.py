"""The seeder's projects and their tasks (D-154, D-155)."""

from apps.audit.models import AuditLog
from apps.audit.services.log import build
from apps.directory.services.demo.constants import (
    PROJECT_TASKS,
    PROJECTS,
    SYSTEM_ACTOR,
    TEAM_TASKS,
)
from apps.projects.models import Project, Task
from apps.projects.services.projects import assign_code
from apps.timesheets.models import TimeEntry


class ProjectsMixin:
    """Part of _Seeder (__init__.py); uses its attributes (self.rng, self.audit, …)."""

    def _projects(self):
        """The projects, each with its allowed tasks (the 9 default tasks come from migration
        timesheets/0007, D-148, D-154)."""
        projects = []
        for name, active in PROJECTS:  # the app's own I-code rule (D-155)
            project = assign_code(Project(name=name, active=active))
            project.save()
            projects.append(project)
        self.tasks = {t.code: t for t in Task.objects.all()}
        for project in projects:
            codes = PROJECT_TASKS[project.code]
            project.tasks.set([self.tasks[c] for c in codes])
            self.audit.append(
                build(
                    AuditLog.Action.CREATE,
                    "Project",
                    project.code,
                    system_actor=SYSTEM_ACTOR,
                    after={
                        "code": project.code,
                        "name": project.name,
                        "active": project.active,
                        "tasks": list(codes),
                    },
                )
            )
        return {p.code: p for p in projects}

    def _task_for(self, project, team):
        """A task the team usually books to and the project allows (D-154)."""
        allowed = PROJECT_TASKS[project.code]
        usual = [c for c in TEAM_TASKS[team] if c in allowed] or list(allowed)
        return self.tasks[self.rng.choice(usual)]

    def _book_tasks(self, week):
        for entry in week.entries:
            if entry.category == TimeEntry.Category.PROJECT:
                entry.task = self._task_for(entry.project, week.employee.team.name)
