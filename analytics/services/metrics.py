"""Personal dashboard metrics (FR-5, D-74–D-80).

Everything here reuses an existing rule instead of re-implementing it:
calendar.week_state (status, deadline, missed — D-34, D-75), summary.summarize (Hours worked,
Break never counted — D-41), calendar expected minutes (prorated, D-19) and payroll
split_hours (overtime — D-64), so the dashboard always agrees with the timesheet pages and
with payroll. load() runs a fixed number of queries whatever the range; the rest is pure.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from django.db.models import Prefetch

from payroll.services.hours import HoursSplit, split_hours
from timesheets.models import PeriodApproval, TimeEntry, Timesheet
from timesheets.services.calendar import (
    OUTSIDE_EMPLOYMENT,
    WeekState,
    active_weekdays,
    company_tz,
    current_period,
    employed_on,
    period_start_for,
    week_start_for,
    week_state,
)
from timesheets.services.summary import WeekSummary, summarize
from timesheets.services.validation import CATEGORY_LABELS

RANGES = (4, 12, 26)
DEFAULT_RANGE = 12
SUBMITTED_STATUSES = (Timesheet.Status.SUBMITTED, Timesheet.Status.APPROVED)


def range_weeks(value):
    """?weeks= → 4, 12 or 26; anything else → 12 (D-74)."""
    try:
        weeks = int(value)
    except (TypeError, ValueError):
        return DEFAULT_RANGE
    return weeks if weeks in RANGES else DEFAULT_RANGE


def week_starts(now, weeks):
    """The last `weeks` Mondays, oldest first, ending with the current week (D-74)."""
    current = week_start_for(now.astimezone(company_tz()).date())
    return [current - timedelta(weeks=i) for i in reversed(range(weeks))]


@dataclass
class WeekRow:
    employee: object
    week_start: date
    state: WeekState
    summary: WeekSummary
    entries: list
    split: HoursSplit | None  # only for SUBMITTED / APPROVED weeks (D-76)

    @property
    def sheet(self):
        return self.state.timesheet


def week_rows(employee, starts, sheets, now):
    """One row per week the person was employed in (D-19); weeks fully outside are left out."""
    rows = []
    for start in starts:
        sheet = sheets.get(start)
        state = week_state(employee, start, sheet, now)
        if state.status == OUTSIDE_EMPLOYMENT:
            continue
        entries = list(sheet.entries.all()) if sheet else []
        summary = summarize(entries, employee, start)
        submitted = sheet is not None and sheet.status in SUBMITTED_STATUSES
        split = split_hours(entries, summary.expected) if submitted else None
        rows.append(WeekRow(employee, start, state, summary, entries, split))
    return rows


def outcome(row, now):
    """ "on_time", "late", "missed", or None when the week doesn't count (yet) (D-75).

    A week counts once its deadline has passed and the person was employed on a weekday of
    it (D-19). Missed = never submitted (the same rule as the /timesheets/ badge); otherwise
    the first submission decides (is_late, D-52).
    """
    if row.state.is_missed:
        return "missed"
    if now < row.state.deadline or active_weekdays(row.employee, row.week_start) == 0:
        return None
    if row.sheet is None or row.sheet.submitted_at is None:
        return None
    return "late" if row.sheet.is_late else "on_time"


@dataclass
class Punctuality:
    on_time: int = 0
    late: int = 0
    missed: int = 0

    @property
    def counted(self):
        return self.on_time + self.late + self.missed

    @property
    def rate(self):
        """On-time share as a whole percent, or None when no week counts yet."""
        return round(100 * self.on_time / self.counted) if self.counted else None


def punctuality(rows, now):
    result = Punctuality()
    for row in rows:
        kind = outcome(row, now)
        if kind:
            setattr(result, kind, getattr(result, kind) + 1)
    return result


def hours_by_project(rows):
    """[(code, name, minutes)], largest first — Project work rows only."""
    totals = {}
    for row in rows:
        for e in row.entries:
            if e.category == TimeEntry.Category.PROJECT and e.project is not None:
                code, name, minutes = totals.get(
                    e.project.code, (e.project.code, e.project.name, 0)
                )
                totals[e.project.code] = (code, name, minutes + e.minutes)
    return sorted(totals.values(), key=lambda t: (-t[2], t[0]))


@dataclass
class Categories:
    rows: list = field(default_factory=list)  # [(label, minutes)] work + leave, fixed order
    break_minutes: int = 0  # shown apart: unpaid, never in a total (D-39, D-77)

    @property
    def total(self):
        return sum(minutes for _, minutes in self.rows)


def hours_by_category(rows):
    minutes = dict.fromkeys(CATEGORY_LABELS, 0)
    for row in rows:
        for e in row.entries:
            minutes[e.category] += e.minutes
    result = Categories(break_minutes=minutes.pop(TimeEntry.Category.BREAK))
    result.rows = [(CATEGORY_LABELS[c], m) for c, m in minutes.items() if m]
    return result


@dataclass
class Overtime:
    minutes: int = 0
    weeks: int = 0  # weeks with any overtime


def overtime(rows):
    """Overtime of SUBMITTED / APPROVED weeks, by the payroll rule (D-64, D-76)."""
    result = Overtime()
    for row in rows:
        if row.split and row.split.overtime:
            result.minutes += row.split.overtime
            result.weeks += 1
    return result


@dataclass
class PeriodOutcome:
    period_start: date
    status: str  # APPROVED / REJECTED / PENDING / IN_PROGRESS
    approval: PeriodApproval | None


def approval_outcomes(employee, starts, approvals, now):
    """Each pay period overlapping the range with employment; current one "in progress" (D-78)."""
    current = current_period(now)
    outcomes = []
    for period in sorted({period_start_for(start) for start in starts}):
        if not any(employed_on(employee, period + timedelta(days=i)) for i in range(14)):
            continue
        approval = approvals.get(period)
        if period == current:
            status = "IN_PROGRESS"
        else:
            status = approval.status if approval else PeriodApproval.Status.PENDING
        outcomes.append(PeriodOutcome(period, status, approval))
    return outcomes


@dataclass
class CurrentWeek:
    state: WeekState
    summary: WeekSummary
    open_until: datetime | None  # what the countdown counts to; None when closed


def current_week(employee, sheet, now):
    start = week_start_for(now.astimezone(company_tz()).date())
    state = week_state(employee, start, sheet, now)
    open_until = None
    if state.editable:
        reopened = sheet is not None and sheet.status == Timesheet.Status.REOPENED
        open_until = sheet.reopen_until if reopened else state.deadline
    entries = list(sheet.entries.all()) if sheet else []
    return CurrentWeek(state, summarize(entries, employee, start), open_until)


@dataclass
class Dashboard:
    employee: object
    now: datetime
    weeks: int
    starts: list
    rows: list
    current: CurrentWeek
    punctuality: Punctuality
    projects: list
    categories: Categories
    overtime: Overtime
    periods: list

    @property
    def worked(self):
        return sum(row.summary.worked for row in self.rows)

    @property
    def expected(self):
        return sum(row.summary.expected for row in self.rows)

    @property
    def outcome_counts(self):
        counts = {"APPROVED": 0, "REJECTED": 0, "PENDING": 0}
        for p in self.periods:
            if p.status in counts:
                counts[p.status] += 1
        return counts

    @property
    def is_empty(self):
        return not any(row.entries for row in self.rows)

    @property
    def chart_data(self):
        """Plain values for json_script (D-80)."""
        return {
            "weeks": [
                {
                    "label": row.week_start.strftime("%b %-d"),
                    "worked": round(row.summary.worked / 60, 2),
                    "expected": round(row.summary.expected / 60, 2),
                }
                for row in self.rows
            ],
            "projects": [
                {"label": code, "hours": round(m / 60, 2)} for code, _, m in self.projects
            ],
            "categories": [
                {"label": label, "hours": round(m / 60, 2)} for label, m in self.categories.rows
            ],
        }


def load(employee, starts):
    """Two database reads, whatever the range: the weeks (with entries) and the approvals."""
    sheets = {
        s.week_start: s
        for s in Timesheet.objects.filter(
            employee=employee, week_start__in=starts
        ).prefetch_related(
            Prefetch("entries", queryset=TimeEntry.objects.select_related("project"))
        )
    }
    periods = {period_start_for(start) for start in starts}
    approvals = {
        a.period_start: a
        for a in PeriodApproval.objects.filter(
            employee=employee, period_start__in=periods
        ).select_related("approver")
    }
    return sheets, approvals


def dashboard_for(employee, weeks, now):
    """Everything the dashboard parts show, for one employee (D-79)."""
    starts = week_starts(now, weeks)
    sheets, approvals = load(employee, starts)
    rows = week_rows(employee, starts, sheets, now)
    return Dashboard(
        employee=employee,
        now=now,
        weeks=weeks,
        starts=starts,
        rows=rows,
        current=current_week(employee, sheets.get(starts[-1]), now),
        punctuality=punctuality(rows, now),
        projects=hours_by_project(rows),
        categories=hours_by_category(rows),
        overtime=overtime(rows),
        periods=approval_outcomes(employee, starts, approvals, now),
    )
