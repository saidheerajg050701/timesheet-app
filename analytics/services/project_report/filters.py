"""The report's filters, read from the URL (D-161, D-165): period → whole Sunday–Saturday
weeks, projects, Hours, and for managers People and Group by."""

from dataclasses import dataclass, field
from datetime import date, timedelta

from django.core.exceptions import PermissionDenied

from analytics.services.project_report.constants import (
    GROUPS,
    HOURS,
    MAX_WEEKS,
    PERIODS,
    SCOPES,
)
from directory.models import Employee
from timesheets.models import Project
from timesheets.services.calendar import (
    company_tz,
    current_period,
    default_period,
    period_end_for,
    week_start_for,
)


@dataclass
class Filters:
    period: str
    start: date  # a Sunday
    end: date  # a Saturday
    hours: str
    projects: list  # Project objects; empty = all projects
    scope: str = "tree"
    manager: Employee | None = None  # scope "manager"
    group: str = "team"  # "" when no grouping would change anything (D-165)
    show_empty: bool = True
    messages: list = field(default_factory=list)
    scopes: list = field(default_factory=list)  # People choices that change the result
    groups: list = field(default_factory=list)  # Group by choices that change the result

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
            if self.scopes:
                params["scope"] = self.scope
            if self.manager is not None:
                params["manager"] = self.manager.employee_code
            if self.group:
                params["group"] = self.group
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
        if managing and self.scopes:
            scope = SCOPES[self.scope]
            if self.manager is not None:
                scope = f"{scope}: {self.manager.first_name} {self.manager.last_name}"
            rows.append(("Scope", scope))
        if managing and self.group:
            rows.append(("Group by", GROUPS[self.group]))
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


def read_filters(params, viewer, now, managing, scopes=()):
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
        # A People choice that wouldn't change anything is not offered; asked for anyway, it
        # quietly falls back to the whole tree (D-165) — never more than the viewer may see.
        filters.scopes = list(scopes)
        filters.scope = params.get("scope") if params.get("scope") in scopes else "tree"
        filters.group = params.get("group") if params.get("group") in GROUPS else "team"
        filters.show_empty = params.get("empty") != "0"
        if filters.scope == "manager":
            code = params.get("manager", "")
            filters.manager = Employee.objects.filter(employee_code=code).first()
            if filters.manager is None:
                raise PermissionDenied("Not allowed.")  # unknown is treated like not visible
    return filters
