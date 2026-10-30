"""Reports → Project budget (Change 12, D-169–D-171): the one place for labour cost.

Built on the Project hours report (services/project_report/) with Approved hours only, so its hours
always equal that report with "Approved". Each Project-work entry costs
hours × the person's hourly rate in force on its work date (apps/compensation/services/pay.py),
rounded to cents; every total is the sum of those rounded rows, so the page, the Excel and the
CSV always add up. Break, leave and non-project time are never charged to projects; overtime
uses the same rate (no premium). An entry whose person has no pay on that date is not costed
(never $0): it is listed as "Rate missing".

The budget compares with the project's whole approved cost since its "costs count from" date
— everyone's, whatever the period or the people in the report; the period filter only changes
the "this period" figures and the breakdowns.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import QueryDict

from apps.compensation.models import PayRecord
from apps.compensation.services.access import can_see_costs, can_see_everyones_costs
from apps.compensation.services.pay import labour_cost, rate_index, record_on
from apps.projects.models import Project
from apps.projects.services.tasks import TASK_NOT_RECORDED
from apps.reports.services.project_report import by_manager, by_team, project_report
from apps.timesheets.models import TimeEntry, Timesheet
from apps.timesheets.services.calendar import period_end_for, period_start_for

ZERO = Decimal("0.00")
RATE_MISSING = "Rate missing"
NOTES = (
    "Rates are the hourly pay HR set for each person.",
    "Overtime premium not included: overtime hours use the same hourly rate.",
    "Approved hours only.",
)
PAY_TYPES = dict(PayRecord.PayType.choices)
ON_TRACK, AT_RISK, OVER, NO_BUDGET = "On track", "At risk", "Over budget", "No budget set"


def budget_status(budget, cost):
    """(percent used or None, status) with the settings' thresholds (80 % / 100 %)."""
    if budget is None:
        return None, NO_BUDGET
    if budget == 0:
        return None, OVER if cost > 0 else ON_TRACK
    used = (cost * 100 / budget).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    if used > settings.BUDGET_OVER_PERCENT:
        return used, OVER
    if used >= settings.BUDGET_AT_RISK_PERCENT:
        return used, AT_RISK
    return used, ON_TRACK


@dataclass
class CostRow:
    """One Project-work entry with its price: the Excel "Detail" tab and the CSV. The cost is
    worked out once, when the row is made."""

    detail: object  # project_report.DetailRow
    pay: PayRecord | None
    rate: Decimal | None = field(init=False)
    cost: Decimal | None = field(init=False)
    pay_type: str = field(init=False)

    def __post_init__(self):
        self.rate = self.pay.hourly_rate if self.pay else None
        self.cost = labour_cost(self.detail.minutes, self.rate) if self.pay else None
        self.pay_type = PAY_TYPES[self.pay.pay_type] if self.pay else RATE_MISSING


@dataclass
class Line:
    """A breakdown line: hours, cost, and hours that have no pay rate (not costed)."""

    label: str
    minutes: int = 0
    cost: Decimal = ZERO
    unpriced: int = 0
    key: object = None

    def add(self, row):
        self.minutes += row.detail.minutes
        if row.pay is None:
            self.unpriced += row.detail.minutes
        else:
            self.cost += row.cost


@dataclass
class ProjectLine(Line):
    project: Project | None = None
    people: set = field(default_factory=set)
    total_cost: Decimal = ZERO  # whole project, approved, since costs_from
    total_unpriced: int = 0

    @property
    def budget(self):
        return self.project.budget

    @property
    def remaining(self):
        return None if self.budget is None else self.budget - self.total_cost

    @property
    def used(self):
        return budget_status(self.budget, self.total_cost)[0]

    @property
    def status(self):
        return budget_status(self.budget, self.total_cost)[1]


@dataclass
class MissingLine:
    person: object  # project_report.PersonRow
    minutes: int = 0
    dates: list = field(default_factory=list)


@dataclass
class CostReport:
    hours: object  # the ProjectReport these costs are built on
    rows: list  # CostRow
    by_project: list  # ProjectLine, by I-code
    by_task: list  # Line
    by_pay_type: list  # Line: Salaried, Hourly, Rate missing
    by_pay_period: list  # Line
    by_team: list  # GroupRow with cost (Group by = Team)
    by_manager: list  # GroupRow with cost (Group by = Manager)
    people: list  # PersonRow with project hours, with cost and unpriced
    missing: list  # MissingLine

    @property
    def viewer(self):
        return self.hours.viewer

    @property
    def filters(self):
        return self.hours.filters

    @property
    def minutes(self):
        return sum(r.detail.minutes for r in self.rows)

    @property
    def cost(self):
        return sum((r.cost for r in self.rows if r.pay), ZERO)

    @property
    def unpriced(self):
        return sum(r.detail.minutes for r in self.rows if r.pay is None)

    @cached_property
    def pay_used(self):
        """{employee id: (pay types, hourly rates)} used for their entries in this report —
        what By employee shows (never a salary, D-170)."""
        used = {}
        for row in self.rows:
            if row.pay is not None:
                types, rates = used.setdefault(row.detail.person.employee.pk, (set(), set()))
                types.add(row.pay.get_pay_type_display())
                rates.add(row.pay.hourly_rate)
        return {pk: (sorted(t), sorted(r)) for pk, (t, r) in used.items()}

    @property
    def chart_data(self):
        return [
            {
                "label": p.project.code,
                "cost": float(p.total_cost),
                "budget": float(p.budget) if p.budget is not None else None,
            }
            for p in self.by_project
        ]


def approved_params(params):
    """The page's filters with Hours forced to Approved: all money uses approved hours."""
    query = QueryDict(mutable=True)
    for key in params:
        if key != "hours":
            query.setlist(key, params.getlist(key))
    query["hours"] = "approved"
    return query


def project_costs(viewer, params, now):
    """The Project budget report for `viewer` (D-169, D-170)."""
    if not can_see_costs(viewer):
        raise PermissionDenied("Project budget is for managers, payroll and HR.")
    everyone = can_see_everyones_costs(viewer)
    hours = project_report(viewer, approved_params(params), now, everyone=everyone)
    people = {p.employee.pk: p for p in hours.people}
    pay = rate_index(list(people))
    rows = []
    for d in hours.detail:
        if d.category == TimeEntry.Category.PROJECT:
            rows.append(CostRow(d, record_on(pay.get(d.person.employee.pk, []), d.work_date)))
    for row in rows:
        person = row.detail.person
        if row.pay is None:
            person.unpriced += row.detail.minutes
        else:
            person.cost += row.cost
    projects = _project_lines(hours, rows, everyone)
    lines = {"task": {}, "type": {}, "period": {}}
    missing = {}
    for row in rows:
        task = row.detail.task
        key = (task.sort_order, task.code) if task else (10**6, "")
        label = f"{task.code} {task.name}" if task else TASK_NOT_RECORDED
        lines["task"].setdefault(key, Line(label, key=key)).add(row)
        lines["type"].setdefault(row.pay_type, Line(row.pay_type)).add(row)
        start = period_start_for(row.detail.work_date)
        label = f"{start:%b %-d} – {period_end_for(start):%b %-d, %Y}"
        lines["period"].setdefault(start, Line(label, key=start)).add(row)
        if row.pay is None:
            line = missing.setdefault(row.detail.person.employee.pk, MissingLine(row.detail.person))
            line.minutes += row.detail.minutes
            if row.detail.work_date not in line.dates:
                line.dates.append(row.detail.work_date)
    type_order = ["Salaried", "Hourly", RATE_MISSING]
    listed = [p for p in hours.people if p.project]
    return CostReport(
        hours=hours,
        rows=rows,
        by_project=projects,
        by_task=[lines["task"][k] for k in sorted(lines["task"])],
        by_pay_type=[lines["type"][t] for t in type_order if t in lines["type"]],
        by_pay_period=[lines["period"][k] for k in sorted(lines["period"])],
        by_team=by_team(hours.people) if "team" in hours.filters.groups else [],
        by_manager=by_manager(hours.people, hours.managers)
        if "manager" in hours.filters.groups
        else [],
        people=listed,
        missing=sorted(
            missing.values(), key=lambda m: (m.person.employee.last_name, m.person.name)
        ),
    )


def _project_lines(hours, rows, everyone):
    """Per project: this period's hours and cost for the report's people, and the whole
    project's approved cost since costs_from (everyone, any date) for the budget."""
    lines = {}
    for row in rows:
        project = row.detail.project
        line = lines.setdefault(project.pk, ProjectLine(project.code, project=project))
        line.add(row)
        line.people.add(row.detail.person.employee.pk)
    chosen = hours.filters.projects
    if chosen:
        for project in chosen:
            lines.setdefault(project.pk, ProjectLine(project.code, project=project))
        lines = {pk: line for pk, line in lines.items() if pk in {p.pk for p in chosen}}
    elif everyone:  # admins and payroll: every project with a budget, even without hours here
        for project in Project.objects.filter(budget__isnull=False):
            lines.setdefault(project.pk, ProjectLine(project.code, project=project))
    _whole_project_costs(lines)
    return sorted(lines.values(), key=lambda line: line.project.number)


def _whole_project_costs(lines):
    """Each listed project's approved cost since costs_from, everyone's (two reads)."""
    if not lines:
        return
    since = {pk: line.project.costs_from for pk, line in lines.items()}
    entries = list(
        TimeEntry.objects.filter(
            category=TimeEntry.Category.PROJECT,
            project_id__in=list(since),
            timesheet__status=Timesheet.Status.APPROVED,
        ).values_list("project_id", "timesheet__employee_id", "work_date", "minutes")
    )
    pay = rate_index({employee for _, employee, _, _ in entries})
    for project_id, employee, day, minutes in entries:
        start = since[project_id]
        if start is not None and day < start:
            continue
        found = record_on(pay.get(employee, []), day)
        line = lines[project_id]
        if found is None:
            line.total_unpriced += minutes
        else:
            line.total_cost += labour_cost(minutes, found.hourly_rate)
