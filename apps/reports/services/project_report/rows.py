"""The report's rows: one per person, group and counted entry, and the ProjectReport that
holds them (D-161, D-162)."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from apps.directory.models import Employee
from apps.projects.models import Project, Task
from apps.projects.services.tasks import TASK_NOT_RECORDED, charge_code
from apps.reports.services.project_report.constants import hours
from apps.reports.services.project_report.filters import Filters


@dataclass
class PersonRow:
    employee: Employee
    team: str
    department: str
    manager: str
    by_task: dict  # {task code or "": minutes}
    project: int = 0
    non_project: dict = field(default_factory=dict)  # {category: minutes}
    leave: int = 0
    note: str = ""
    cost: Decimal = Decimal("0.00")  # Project budget only: labour cost (D-169)
    unpriced: int = 0  # Project budget only: project minutes without a pay rate

    @property
    def name(self):
        return f"{self.employee.first_name} {self.employee.last_name}"

    @property
    def inactive(self):
        return self.employee.status != Employee.Status.ACTIVE

    @property
    def non_project_total(self):
        return sum(self.non_project.values())

    @property
    def total(self):
        return self.project + self.non_project_total

    @property
    def has_hours(self):
        return self.project > 0


@dataclass
class GroupRow:
    label: str
    people: int = 0
    project: int = 0
    non_project: int = 0
    employee: Employee | None = None  # the manager, for "By manager"
    depth: int = 0
    rollup_project: int = 0  # "Including everyone below" (managers only)
    rollup_non_project: int = 0
    cost: Decimal = Decimal("0.00")  # Project budget only (D-169)
    rollup_cost: Decimal = Decimal("0.00")

    @property
    def total(self):
        return self.project + self.non_project

    @property
    def rollup_total(self):
        return self.rollup_project + self.rollup_non_project


@dataclass
class DetailRow:
    """One counted entry: the CSV and the Excel "Detail" tab (no reasons, D-163)."""

    work_date: date
    week_start: date
    person: PersonRow
    project: Project | None
    task: Task | None
    category: str
    minutes: int
    status: str

    @property
    def charge_code(self):
        return charge_code(self.project, self.task) if self.project else ""


@dataclass
class ProjectReport:
    viewer: Employee
    filters: Filters
    own: bool  # the viewer's own hours only (someone who manages nobody)
    people: list  # PersonRow, every listed person (people with project hours first)
    task_columns: list  # Task objects, then None = "Task not recorded"
    by_project: list  # [(project, minutes, people)]
    matrix: dict  # {(project id, task code or ""): minutes}
    by_week: list  # [(week start, project, non-project)]
    non_project: list  # [(label, minutes)] Meetings, Training, Other
    by_team: list  # GroupRow
    by_manager: list  # GroupRow, depth-first; "No manager in this report" last
    detail: list  # DetailRow
    manager_choices: list = field(default_factory=list)  # managers the viewer may pick (D-160)
    managers: dict = field(default_factory=dict)  # {employee id: manager id}, for regrouping

    @property
    def project_total(self):
        return sum(p.project for p in self.people)

    @property
    def non_project_total(self):
        return sum(p.non_project_total for p in self.people)

    @property
    def total(self):
        return self.project_total + self.non_project_total

    @property
    def with_hours(self):
        return sum(p.has_hours for p in self.people)

    @property
    def shown_people(self):
        """By employee as shown: 0.00 rows hidden when "Show people with no hours" is off."""
        if self.filters.show_empty:
            return self.people
        return [p for p in self.people if p.has_hours]

    @property
    def by_task(self):
        """[(code, name, minutes)] for every task column, "Task not recorded" last."""
        totals = {}
        for (_, code), minutes in self.matrix.items():
            totals[code] = totals.get(code, 0) + minutes
        return [
            (t.code, t.name, totals.get(t.code, 0))
            if t
            else ("", TASK_NOT_RECORDED, totals.get("", 0))
            for t in self.task_columns
        ]

    @property
    def matrix_rows(self):
        """[(project, [minutes per task column], total)] for Project × task."""
        return [(p, self.matrix_row(p), m) for p, m, _ in self.by_project]

    @property
    def employee_rows(self):
        """[(person, [minutes per task column])] for By employee, as shown."""
        return [
            (p, [p.by_task.get(t.code if t else "", 0) for t in self.task_columns])
            for p in self.shown_people
        ]

    def matrix_row(self, project):
        return [self.matrix.get((project.pk, t.code if t else ""), 0) for t in self.task_columns]

    @property
    def chart_data(self):
        return [{"label": p.code, "hours": hours(m)} for p, m, _ in self.by_project]
