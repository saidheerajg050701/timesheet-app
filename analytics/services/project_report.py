"""Reports → Project hours (Change 11, D-160–D-164): the one place for the report's numbers.

The page, the Excel workbook and the CSV all read one ProjectReport, for every role, so they
always agree. Who is in it comes from the same hierarchy rules as Team (permissions.py); weeks
and pay periods from calendar.py; "employed in the range" from team.people_in_range.

Counting (D-161):
- Project hours: Project-work entries for the selected projects (all when none is selected).
- Non-project time: Meetings, Training and Other — never filtered by project.
- Total time = project hours + non-project time. Break and leave never count; leave is shown
  per person for context only.
- Only weeks whose status matches the Hours filter count (approved / + submitted / all).

Loading is a fixed number of database reads, whatever the number of people or weeks (D-164).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from types import SimpleNamespace

from django.core.exceptions import PermissionDenied

from analytics.services.team import people_in_range
from directory.models import Employee
from directory.services.permissions import manager_map, reporting_tree_ids
from timesheets.models import Project, Task, TimeEntry, Timesheet
from timesheets.services.calendar import (
    company_tz,
    current_period,
    default_period,
    effective_status,
    period_end_for,
    week_start_for,
)
from timesheets.services.tasks import TASK_NOT_RECORDED, charge_code
from timesheets.services.validation import CATEGORY_LABELS

PERIODS = {
    "this": "This pay period",
    "last": "Last pay period",
    "4w": "Last 4 weeks",
    "12w": "Last 12 weeks",
    "custom": "Custom dates",
}
HOURS = {  # the Hours filter: which weeks count, by their stored status (D-161)
    "approved": ("Approved", {Timesheet.Status.APPROVED}),
    "submitted": ("Approved + Submitted", {Timesheet.Status.APPROVED, Timesheet.Status.SUBMITTED}),
    "all": ("Everything entered", None),
}
SCOPES = {"tree": "Whole tree", "direct": "Direct reports only", "manager": "One manager's group"}
GROUPS = {"team": "Team", "manager": "Manager"}
MAX_WEEKS = 53
NON_PROJECT = (TimeEntry.Category.MEETING, TimeEntry.Category.TRAINING, TimeEntry.Category.OTHER)
NO_TEAM = "No team"
NO_MANAGER = "No manager in this report"
FOOTNOTE = "Teams and managers are as they are today (moves are not tracked)."
# Why a listed person has 0.00 project hours, in this order (D-162)
NOT_APPROVED, OTHER_PROJECTS, ONLY_NON_PROJECT, ON_LEAVE, NO_TIME = (
    "Hours not approved yet",
    "Worked on other projects",
    "Only non-project time",
    "On leave",
    "No time entered",
)


def hours(minutes):
    """Minutes → hours as a number with 2 decimals (the page, the Excel and the CSV)."""
    return round(minutes / 60, 2)


# --- filters -------------------------------------------------------------------------------


@dataclass
class Filters:
    period: str
    start: date  # a Sunday
    end: date  # a Saturday
    hours: str
    projects: list  # Project objects; empty = all projects
    scope: str = "tree"
    manager: Employee | None = None  # scope "manager"
    group: str = "team"
    show_empty: bool = True
    messages: list = field(default_factory=list)

    @property
    def starts(self):
        """The Sundays of the report's weeks, oldest first."""
        return [
            self.start + timedelta(weeks=i) for i in range((self.end - self.start).days // 7 + 1)
        ]

    @property
    def statuses(self):
        return HOURS[self.hours][1]

    @property
    def project_ids(self):
        return {p.pk for p in self.projects}

    def query(self, managing):
        """The filters as URL parameters (also stored in the EXPORT audit row)."""
        params = {"period": self.period, "hours": self.hours}
        if self.period == "custom":
            params.update({"from": self.start.isoformat(), "to": self.end.isoformat()})
        params["project"] = [p.code for p in self.projects]
        if managing:
            params.update({"scope": self.scope, "group": self.group})
            if self.manager is not None:
                params["manager"] = self.manager.employee_code
            if not self.show_empty:
                params["empty"] = "0"
        return params

    def described(self, managing):
        """[(label, value)] for the Summary."""
        rows = [
            ("Period", f"{self.start:%b %-d, %Y} – {self.end:%b %-d, %Y} ({PERIODS[self.period]})"),
            ("Projects", ", ".join(f"{p.code} {p.name}" for p in self.projects) or "All projects"),
            ("Hours", HOURS[self.hours][0]),
        ]
        if managing:
            scope = SCOPES[self.scope]
            if self.manager is not None:
                scope = f"{scope}: {self.manager.first_name} {self.manager.last_name}"
            rows += [("Scope", scope), ("Group by", GROUPS[self.group])]
        return rows


def _date(text):
    try:
        return date.fromisoformat(text or "")
    except ValueError:
        return None


def period_range(period, now, start=None, end=None):
    """(Sunday, Saturday) of a period choice, whole Sunday–Saturday weeks (D-161)."""
    today_week = week_start_for(now.astimezone(company_tz()).date())
    if period == "this":
        first = current_period(now)
        return first, period_end_for(first)
    if period in ("4w", "12w"):
        weeks = int(period[:-1])
        return today_week - timedelta(weeks=weeks - 1), today_week + timedelta(days=6)
    if period == "custom":
        return week_start_for(start), week_start_for(end) + timedelta(days=6)
    first = default_period(now)
    return first, period_end_for(first)


def read_filters(params, viewer, now, managing):
    """The filters from the URL. Bad values fall back to the defaults with a message; for
    someone who manages nobody, any scope, group or manager parameter is refused (403)."""
    if not managing and any(params.get(name) for name in ("scope", "group", "manager")):
        raise PermissionDenied("You can only see your own hours.")
    notes = []
    period = params.get("period") if params.get("period") in PERIODS else "last"
    start = end = None
    if period == "custom":
        start, end = _date(params.get("from")), _date(params.get("to"))
        if start is None or end is None or start > end:
            notes.append(
                "Choose a From date on or before the To date. Showing the last pay period."
            )
            period = "last"
        elif (week_start_for(end) - week_start_for(start)).days // 7 + 1 > MAX_WEEKS:
            notes.append(f"Choose at most {MAX_WEEKS} weeks. Showing the last pay period.")
            period = "last"
    first, last = period_range(period, now, start, end)
    codes = [c.strip().upper() for c in params.getlist("project") if c.strip()]
    found = {p.code: p for p in Project.objects.filter(code__in=codes)}
    unknown = [c for c in codes if c not in found]
    if unknown:
        notes.append(f"Unknown project {', '.join(unknown)} — left out.")
    projects = sorted({found[c] for c in codes if c in found}, key=lambda p: p.number)
    filters = Filters(
        period=period,
        start=first,
        end=last,
        hours=params.get("hours") if params.get("hours") in HOURS else "approved",
        projects=projects,
        messages=notes,
    )
    if managing:
        filters.scope = params.get("scope") if params.get("scope") in SCOPES else "tree"
        filters.group = params.get("group") if params.get("group") in GROUPS else "team"
        filters.show_empty = params.get("empty") != "0"
        if filters.scope == "manager":
            code = params.get("manager", "")
            filters.manager = Employee.objects.filter(employee_code=code).first()
            if filters.manager is None:
                raise PermissionDenied("Not allowed.")  # unknown is treated like not visible
    return filters


# --- who is in the report (D-160) ------------------------------------------------------------


def manages_anyone(viewer, managers):
    return viewer.is_admin or any(m == viewer.pk for m in managers.values())


def report_people(viewer, filters, managers):
    """Ids of the people in the report: the viewer only (someone who manages nobody), or the
    viewer plus their tree / direct reports / one manager's group (everyone for an admin).
    A manager outside what the viewer may see is refused (403)."""
    if not manages_anyone(viewer, managers):
        return {viewer.pk}
    tree = set(managers) if viewer.is_admin else reporting_tree_ids(viewer, managers)
    if filters.scope == "direct":
        return {viewer.pk} | {pk for pk, m in managers.items() if m == viewer.pk}
    if filters.scope == "manager":
        target = filters.manager
        if target.pk != viewer.pk and target.pk not in tree:
            raise PermissionDenied("Not allowed.")
        return {target.pk} | reporting_tree_ids(target, managers)
    return {viewer.pk} | tree


def manager_choices(viewer, managers):
    """The managers whose group the viewer may choose: everyone who manages someone in the
    viewer's tree (anyone for an admin), the viewer included. Sorted by name."""
    leads = {m for m in managers.values() if m is not None}
    visible = set(managers) if viewer.is_admin else reporting_tree_ids(viewer, managers)
    ids = leads & (visible | {viewer.pk})
    return list(Employee.objects.filter(pk__in=ids).order_by("last_name", "first_name"))


# --- the report --------------------------------------------------------------------------------


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


def _status_of(sheets, sheet_id, status, week_start, reopen_until, now):
    if sheet_id not in sheets:
        sheet = SimpleNamespace(status=status, week_start=week_start, reopen_until=reopen_until)
        sheets[sheet_id] = effective_status(sheet, now)
    return sheets[sheet_id]


def project_report(viewer, params, now):
    """The report for `viewer` from URL parameters (D-160–D-164)."""
    managers = manager_map()
    managing = manages_anyone(viewer, managers)
    filters = read_filters(params, viewer, now, managing)
    ids = report_people(viewer, filters, managers)
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
    if managing:
        report.manager_choices = manager_choices(viewer, managers)
    return report


def build_report(viewer, filters, managing, managers, candidates, entries, projects, tasks, now):
    """Everything worked out from the loaded rows; no database reads."""
    allowed, wanted = filters.statuses, filters.project_ids
    sheets, rows, counted_ids = {}, {}, set()
    raw = []  # (employee id, kind, ...) per entry, before the people are known
    for sheet_id, emp_id, week, status, reopen, day, category, project_id, task_id, m in entries:
        counts = allowed is None or status in allowed
        raw.append(
            (sheet_id, emp_id, week, status, reopen, day, category, project_id, task_id, m, counts)
        )
        if counts and (
            category in NON_PROJECT
            or (category == "PROJECT" and (not wanted or project_id in wanted))
        ):
            counted_ids.add(emp_id)
    # Everyone employed in the range (inactive people only with counted hours); one's own
    # report always shows oneself.
    people = people_in_range(candidates, counted_ids, filters.starts) if managing else [viewer]
    for employee in people:
        rows[employee.pk] = PersonRow(
            employee=employee,
            team=employee.team.name if employee.team else NO_TEAM,
            department=employee.team.department if employee.team else "",
            manager=f"{employee.manager.first_name} {employee.manager.last_name}"
            if employee.manager
            else "",
            by_task={},
        )
    flags = {pk: set() for pk in rows}  # what explains a 0.00 row
    matrix, project_people, weeks, detail = {}, {}, {}, []
    for (
        sheet_id,
        emp_id,
        week,
        status,
        reopen,
        day,
        category,
        project_id,
        task_id,
        m,
        counts,
    ) in raw:
        person = rows.get(emp_id)
        if person is None:
            continue
        project, task = projects.get(project_id), tasks.get(task_id)
        is_project = category == TimeEntry.Category.PROJECT
        selected = is_project and (not wanted or project_id in wanted)
        if category in TimeEntry.LEAVE:
            if counts:
                person.leave += m
                flags[emp_id].add(ON_LEAVE)
            continue
        if not counts:
            if selected:
                flags[emp_id].add(NOT_APPROVED)
            continue
        if is_project and not selected:
            flags[emp_id].add(OTHER_PROJECTS)
            continue
        week_row = weeks.setdefault(week, [0, 0])
        if selected:
            code = task.code if task else ""
            person.project += m
            person.by_task[code] = person.by_task.get(code, 0) + m
            matrix[(project_id, code)] = matrix.get((project_id, code), 0) + m
            project_people.setdefault(project_id, set()).add(emp_id)
            week_row[0] += m
        else:
            person.non_project[category] = person.non_project.get(category, 0) + m
            flags[emp_id].add(ONLY_NON_PROJECT)
            week_row[1] += m
        status_now = _status_of(sheets, sheet_id, status, week, reopen, now)
        detail.append(
            DetailRow(
                day, week, person, project if is_project else None, task, category, m, status_now
            )
        )
    for pk, person in rows.items():
        if not person.has_hours:
            found = flags[pk]
            person.note = next(
                (
                    n
                    for n in (NOT_APPROVED, OTHER_PROJECTS, ONLY_NON_PROJECT, ON_LEAVE)
                    if n in found
                ),
                NO_TIME,
            )
    listed = sorted(rows.values(), key=lambda p: not p.has_hours)  # stable: names stay in order
    used = {code for _, code in matrix}
    task_columns = [
        t
        for t in sorted(tasks.values(), key=lambda t: (t.sort_order, t.code))
        if t.active or t.code in used
    ]
    task_columns.append(None)
    totals = {}
    for (project_id, _), minutes in matrix.items():
        totals[project_id] = totals.get(project_id, 0) + minutes
    by_project = [
        (projects[pid], minutes, len(project_people[pid]))
        for pid, minutes in sorted(totals.items(), key=lambda t: projects[t[0]].number)
    ]
    by_week = [(start, *weeks.get(start, (0, 0))) for start in filters.starts]
    non_project = [
        (CATEGORY_LABELS[c], sum(p.non_project.get(c, 0) for p in listed)) for c in NON_PROJECT
    ]
    return ProjectReport(
        viewer=viewer,
        filters=filters,
        own=not managing,
        people=listed,
        task_columns=task_columns,
        by_project=by_project,
        matrix=matrix,
        by_week=by_week,
        non_project=non_project,
        by_team=_by_team(listed) if managing else [],
        by_manager=_by_manager(listed, managers) if managing else [],
        detail=detail,
    )


def _add(group, person):
    group.people += 1
    group.project += person.project
    group.non_project += person.non_project_total


def _by_team(people):
    """[GroupRow] per directory team (as it is today), by name; "No team" last."""
    groups = {}
    for person in people:
        team = person.employee.team
        key = (team is None, team.name if team else "", team.department if team else "")
        label = f"{team.name} ({team.department})" if team else NO_TEAM
        _add(groups.setdefault(key, GroupRow(label)), person)
    return [groups[key] for key in sorted(groups)]


def _by_manager(people, managers):
    """[GroupRow] per manager in the report, depth-first by name (D-162).

    "Own group" = the manager plus direct reports who manage nobody, so every person is
    counted once and the column adds up to the grand total. "Including everyone below" adds
    the groups of the managers under them (the roll-up). People whose manager is not in the
    report and who manage nobody form the last row, "No manager in this report".
    """
    in_report = {p.employee.pk: p for p in people}
    leads = {m for m in managers.values() if m is not None}
    heads = {
        pk: GroupRow(p.name, employee=p.employee) for pk, p in in_report.items() if pk in leads
    }
    orphans = GroupRow(NO_MANAGER)
    for pk, person in in_report.items():
        if pk in heads:
            _add(heads[pk], person)
        elif managers.get(pk) in heads:
            _add(heads[managers[pk]], person)
        else:
            _add(orphans, person)
    children = {}
    for pk in heads:
        children.setdefault(managers.get(pk) if managers.get(pk) in heads else None, []).append(pk)

    def by_name(pk):
        employee = heads[pk].employee
        return (employee.last_name, employee.first_name, employee.employee_code)

    ordered, seen = [], set()

    def visit(pk, depth):
        row = heads[pk]
        seen.add(pk)  # bad data such as A→B→A never loops (like reporting_tree_ids)
        row.depth = depth
        ordered.append(row)
        row.rollup_project, row.rollup_non_project = row.project, row.non_project
        for child in sorted(set(children.get(pk, [])) - seen, key=by_name):
            below = visit(child, depth + 1)
            row.rollup_project += below.rollup_project
            row.rollup_non_project += below.rollup_non_project
        return row

    for root in sorted(children.get(None, []), key=by_name):
        visit(root, 0)
    for pk in sorted(set(heads) - seen, key=by_name):  # a loop with no top: start anywhere
        if pk not in seen:
            visit(pk, 0)
    if orphans.people:
        orphans.rollup_project, orphans.rollup_non_project = orphans.project, orphans.non_project
        ordered.append(orphans)
    return ordered
