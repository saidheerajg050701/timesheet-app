"""Team analytics (FR-6, D-81–D-86).

Built entirely on the Phase 9 metrics (week_rows, punctuality, overtime, hours_by_project,
approval_outcomes), which in turn use week_state, summarize, prorated expected minutes and
the payroll split — no rule is written twice. Loading is a fixed number of queries.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from apps.analytics.services import metrics
from apps.directory.models import Employee
from apps.directory.services.permissions import team_scope
from apps.timesheets.models import PeriodApproval, Timesheet
from apps.timesheets.services.calendar import company_tz, employed_on, week_start_for

SCOPES = ("tree", "direct")
SUBMITTED = (Timesheet.Status.SUBMITTED, Timesheet.Status.APPROVED)


def utilization(worked, available):
    """Whole percent of available hours worked, or None when nothing was available (D-82)."""
    return round(100 * worked / available) if available > 0 else None


@dataclass
class PersonStats:
    employee: Employee
    rows: list
    punctuality: metrics.Punctuality
    overtime: metrics.Overtime
    pending: int
    worked: int  # all weeks in the range (D-77)
    finished_worked: int  # weeks whose deadline has passed (D-82)
    available: int  # expected − leave, finished weeks only (D-82)

    @property
    def utilization(self):
        return utilization(self.finished_worked, self.available)


def person_stats(employee, rows, approvals, starts, now):
    finished = [r for r in rows if now >= r.state.deadline]
    periods = metrics.approval_outcomes(employee, starts, approvals, now)
    return PersonStats(
        employee=employee,
        rows=rows,
        punctuality=metrics.punctuality(rows, now),
        overtime=metrics.overtime(rows),
        pending=sum(p.status == PeriodApproval.Status.PENDING for p in periods),
        worked=sum(r.summary.worked for r in rows),
        finished_worked=sum(r.summary.worked for r in finished),
        available=sum(max(r.summary.expected - r.summary.leave, 0) for r in finished),
    )


SORT_KEYS = {
    "name": lambda s: (s.employee.last_name.lower(), s.employee.first_name.lower()),
    "worked": lambda s: s.worked,
    "utilization": lambda s: -1 if s.utilization is None else s.utilization,
    "on_time": lambda s: -1 if s.punctuality.rate is None else s.punctuality.rate,
    "late": lambda s: s.punctuality.late,
    "missed": lambda s: s.punctuality.missed,
    "overtime": lambda s: s.overtime.minutes,
    "pending": lambda s: s.pending,
}


def sort_people(stats, sort, direction):
    """Server-side sorting by any table column (D-84); unknown columns sort by name."""
    key = SORT_KEYS.get(sort, SORT_KEYS["name"])
    ordered = sorted(stats, key=SORT_KEYS["name"])  # stable tie-break by name
    return sorted(ordered, key=key, reverse=direction == "desc")


@dataclass
class TeamWeek:
    week_start: object
    worked: int = 0
    expected: int = 0


def team_weeks(stats, starts):
    weeks = {start: TeamWeek(start) for start in starts}
    for person in stats:
        for row in person.rows:
            weeks[row.week_start].worked += row.summary.worked
            weeks[row.week_start].expected += row.summary.expected
    return list(weeks.values())


@dataclass
class ComplianceItem:
    employee: Employee
    label: str


def compliance(stats, now):
    """Who hasn't submitted the current week yet, if employed in it (D-83)."""
    current = week_start_for(now.astimezone(company_tz()).date())
    items = []
    for person in stats:
        row = next((r for r in person.rows if r.week_start == current), None)
        if row is None or row.state.status in SUBMITTED:
            continue
        if now < row.state.deadline:
            label = "Not submitted yet"
        elif row.state.is_missed:
            label = "Missed"
        elif row.state.status == Timesheet.Status.REOPENED:
            label = "Reopened"
        else:
            label = "Locked"
        items.append(ComplianceItem(person.employee, label))
    return sorted(items, key=lambda i: (i.employee.last_name, i.employee.first_name))


def team_projects(stats):
    """[(code, name, minutes)] across the selected people, largest first."""
    totals = {}
    for person in stats:
        for code, name, minutes in metrics.hours_by_project(person.rows):
            _, _, sofar = totals.get(code, (code, name, 0))
            totals[code] = (code, name, sofar + minutes)
    return sorted(totals.values(), key=lambda t: (-t[2], t[0]))


def _all_rows(stats):
    return [row for person in stats for row in person.rows]


def team_tasks(stats):
    """hours_by_task across the selected people (D-153)."""
    return metrics.hours_by_task(_all_rows(stats))


def team_charge_codes(stats):
    """hours_by_charge_code across the selected people (D-153)."""
    return metrics.hours_by_charge_code(_all_rows(stats))


def people_in_range(candidates, sheets, starts):
    """Employed on a day of the range; inactive people only with a timesheet in it (D-81)."""
    first, last = starts[0], starts[-1] + timedelta(days=6)
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    people = []
    for employee in candidates:
        if not any(employed_on(employee, d) for d in days):
            continue
        if employee.status != Employee.Status.ACTIVE and employee.pk not in sheets:
            continue
        people.append(employee)
    return people


@dataclass
class TeamDashboard:
    viewer: Employee
    scope: str
    team_id: int | None
    weeks: int
    starts: list
    sort: str
    direction: str
    teams: list  # [(id, name)] among the people in scope, for the filter
    people: list = field(default_factory=list)  # PersonStats, sorted
    by_week: list = field(default_factory=list)
    compliance: list = field(default_factory=list)
    projects: list = field(default_factory=list)
    tasks: list = field(default_factory=list)
    charge_codes: list = field(default_factory=list)

    @property
    def worked(self):
        return sum(p.worked for p in self.people)

    @property
    def utilization(self):
        """Team average, weighted by available hours (D-82)."""
        return utilization(
            sum(p.finished_worked for p in self.people), sum(p.available for p in self.people)
        )

    @property
    def chart_data(self):
        return {
            "weeks": [
                {
                    "label": w.week_start.strftime("%b %-d"),
                    "worked": round(w.worked / 60, 2),
                    "expected": round(w.expected / 60, 2),
                }
                for w in self.by_week
            ],
            "projects": [
                {"label": code, "hours": round(m / 60, 2)} for code, _, m in self.projects
            ],
            "tasks": metrics.task_chart(self.tasks),
        }


def team_dashboard(
    viewer,
    *,
    scope="tree",
    team_id=None,
    weeks=metrics.DEFAULT_RANGE,
    sort="name",
    direction="asc",
    now,
):
    """The team page for `viewer` (D-81–D-86). Only people in the viewer's scope are loaded."""
    scope = scope if scope in SCOPES else "tree"
    starts = metrics.week_starts(now, weeks)
    candidates = list(
        Employee.objects.filter(pk__in=team_scope(viewer, scope))
        .select_related("team")
        .order_by("last_name", "first_name")
    )
    sheets, approvals = metrics.load_many(candidates, starts)
    in_range = people_in_range(candidates, sheets, starts)
    teams = sorted({(e.team.pk, e.team.name) for e in in_range if e.team}, key=lambda t: t[1])
    if team_id is not None:
        in_range = [e for e in in_range if e.team_id == team_id]
    stats = [
        person_stats(
            e,
            metrics.week_rows(e, starts, sheets.get(e.pk, {}), now),
            approvals.get(e.pk, {}),
            starts,
            now,
        )
        for e in in_range
    ]
    return TeamDashboard(
        viewer=viewer,
        scope=scope,
        team_id=team_id,
        weeks=weeks,
        starts=starts,
        sort=sort if sort in SORT_KEYS else "name",
        direction="desc" if direction == "desc" else "asc",
        teams=teams,
        people=sort_people(stats, sort, direction),
        by_week=team_weeks(stats, starts),
        compliance=compliance(stats, now),
        projects=team_projects(stats),
        tasks=team_tasks(stats),
        charge_codes=team_charge_codes(stats),
    )
