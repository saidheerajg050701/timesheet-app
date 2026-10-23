"""Weeks, deadlines, pay periods and week status (B.9 #1–#5).

week_start_for, deadline_for and pay_period_for were built early for seed_demo (D-25).
Status is worked out when read; opening a page never writes anything (D-34).
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

from timesheets.models import Timesheet

DEADLINE_WEEKDAY_OFFSET = 5  # Saturday = Monday + 5 days
DEADLINE_TIME = time(12, 0)  # noon company time (B.1 row 10)


def week_start_for(d: date) -> date:
    """Monday of the Monday→Sunday week containing d."""
    return d - timedelta(days=d.weekday())


def deadline_for(week_start: date, tz) -> datetime:
    """Saturday 12:00 company time of the given week. zoneinfo handles daylight saving."""
    saturday = week_start + timedelta(days=DEADLINE_WEEKDAY_OFFSET)
    return datetime.combine(saturday, DEADLINE_TIME, tzinfo=tz)


def pay_period_for(d: date, anchor: date) -> tuple[date, date, date]:
    """(period_start, week1, week2) of the 2-week pay period containing d.

    Periods repeat every 14 days from `anchor` (a Monday), in both directions.
    """
    weeks_since_anchor = (week_start_for(d) - anchor).days // 7
    period_start = anchor + timedelta(weeks=weeks_since_anchor - weeks_since_anchor % 2)
    return period_start, period_start, period_start + timedelta(weeks=1)


def company_tz():
    return ZoneInfo(settings.COMPANY_TZ)


def effective_status(timesheet, now: datetime) -> str:
    """Stored status, plus the time rules (D-08, D-21).

    DRAFT becomes LOCKED at Saturday 12:00; REOPENED becomes LOCKED at reopen_until.
    """
    status = timesheet.status
    if status == Timesheet.Status.DRAFT:
        if now >= deadline_for(timesheet.week_start, company_tz()):
            return Timesheet.Status.LOCKED
    elif status == Timesheet.Status.REOPENED:
        if timesheet.reopen_until and now >= timesheet.reopen_until:
            return Timesheet.Status.LOCKED
    return status


def employed_on(employee, day: date) -> bool:
    """Within hire_date…end_date (either may be empty) (D-19)."""
    if employee.hire_date and day < employee.hire_date:
        return False
    return not (employee.end_date and day > employee.end_date)


def week_days(week_start: date) -> list[date]:
    return [week_start + timedelta(days=i) for i in range(7)]


def active_weekdays(employee, week_start: date) -> int:
    """Employed days Monday–Friday in the week (D-19)."""
    return sum(employed_on(employee, day) for day in week_days(week_start)[:5])


def expected_minutes_for(employee, week_start: date) -> int:
    """expected_weekly_minutes × active weekdays / 5; 0 for weeks outside employment (D-19)."""
    return round(employee.expected_weekly_minutes * active_weekdays(employee, week_start) / 5)


NOT_STARTED = "NOT_STARTED"  # no timesheet yet, still open
OUTSIDE_EMPLOYMENT = "OUTSIDE_EMPLOYMENT"  # not employed on any day of the week


@dataclass(frozen=True)
class WeekState:
    week_start: date
    status: str
    deadline: datetime
    editable: bool
    is_missed: bool
    expected_minutes: int
    timesheet: Timesheet | None


def week_state(employee, week_start: date, timesheet, now: datetime) -> WeekState:
    """Everything the pages need to know about one employee-week at time `now` (FR-8)."""
    deadline = deadline_for(week_start, company_tz())
    current_week = week_start_for(now.astimezone(company_tz()).date())
    employed_any_day = any(employed_on(employee, day) for day in week_days(week_start))
    if timesheet is not None:
        status = effective_status(timesheet, now)
    elif not employed_any_day:
        status = OUTSIDE_EMPLOYMENT
    else:
        status = Timesheet.Status.LOCKED if now >= deadline else NOT_STARTED
    editable = week_start <= current_week and status in (  # no future weeks (D-33)
        NOT_STARTED,
        Timesheet.Status.DRAFT,
        Timesheet.Status.REOPENED,
    )
    weekdays = active_weekdays(employee, week_start)
    return WeekState(
        week_start=week_start,
        status=status,
        deadline=deadline,
        editable=editable,
        # Missed: locked without a submission while employed on a weekday (D-19).
        is_missed=status == Timesheet.Status.LOCKED and weekdays > 0,
        expected_minutes=expected_minutes_for(employee, week_start),
        timesheet=timesheet,
    )
