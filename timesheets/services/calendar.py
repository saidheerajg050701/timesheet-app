"""Weeks, deadlines, pay periods and week status (B.9 #1–#5).

week_start_for, deadline_for and pay_period_for were built early for seed_demo (D-25).
Status is worked out when read; opening a page never writes anything (D-34).

A week runs Sunday → Saturday and is identified by its Sunday (D-111); the deadline is its
last day, Saturday 12:00 (D-112); working days are Monday–Friday (D-114). This module is the
only place those rules live.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

from timesheets.models import Timesheet

WEEK_START_WEEKDAY = 6  # Sunday (date.weekday(): Monday = 0 … Sunday = 6) (D-111)
DEADLINE_DAY_OFFSET = 6  # Saturday = Sunday + 6 days: the last day of the week (D-112)
DEADLINE_TIME = time(12, 0)  # noon company time (B.1 row 10)
WORKING_WEEKDAYS = range(0, 5)  # Monday–Friday (D-19, D-114)


def week_start_for(d: date) -> date:
    """Sunday of the Sunday→Saturday week containing d (D-111)."""
    return d - timedelta(days=(d.weekday() - WEEK_START_WEEKDAY) % 7)


def deadline_for(week_start: date, tz) -> datetime:
    """Saturday 12:00 company time of the given week. zoneinfo handles daylight saving."""
    saturday = week_start + timedelta(days=DEADLINE_DAY_OFFSET)
    return datetime.combine(saturday, DEADLINE_TIME, tzinfo=tz)


def reopen_until_for(week_start: date, at: datetime) -> datetime:
    """End of a reopen window: the later of `at` + 48 hours and the week's deadline (D-21)."""
    return max(at + timedelta(hours=48), deadline_for(week_start, company_tz()))


def pay_period_for(d: date, anchor: date) -> tuple[date, date, date]:
    """(period_start, week1, week2) of the 2-week pay period containing d.

    Periods repeat every 14 days from `anchor`, which must be a Sunday (D-113), in both
    directions.
    """
    check_anchor(anchor)
    weeks_since_anchor = (week_start_for(d) - anchor).days // 7
    period_start = anchor + timedelta(weeks=weeks_since_anchor - weeks_since_anchor % 2)
    return period_start, period_start, period_start + timedelta(weeks=1)


def anchor_problem(anchor: date) -> str | None:
    """Why `anchor` can't start pay periods, or None if it can (D-113)."""
    if anchor.weekday() != WEEK_START_WEEKDAY:
        return (
            f"PAY_PERIOD_ANCHOR {anchor.isoformat()} is a {anchor:%A}; it must be a Sunday "
            f"(the first day of a week), e.g. {week_start_for(anchor).isoformat()}."
        )
    return None


def check_anchor(anchor: date) -> None:
    if problem := anchor_problem(anchor):
        raise ValueError(problem)


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


def working_days(week_start: date) -> list[date]:
    """Monday–Friday of the week; Sunday and Saturday are the weekend at its ends (D-114)."""
    return [day for day in week_days(week_start) if day.weekday() in WORKING_WEEKDAYS]


def active_weekdays(employee, week_start: date) -> int:
    """Employed days Monday–Friday in the week (D-19)."""
    return sum(employed_on(employee, day) for day in working_days(week_start))


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
        # Missed: deadline passed, employed on a weekday (D-19), and never submitted (D-75).
        # A re-locked week counts by its first submission instead.
        is_missed=now >= deadline
        and weekdays > 0
        and (timesheet is None or timesheet.submitted_at is None),
        expected_minutes=expected_minutes_for(employee, week_start),
        timesheet=timesheet,
    )


# --- pay periods for the approvals page (D-54) -------------------------------------------


def period_start_for(day: date) -> date:
    """Sunday of week 1 of the 14-day pay period containing `day` (PAY_PERIOD_ANCHOR)."""
    return pay_period_for(day, settings.PAY_PERIOD_ANCHOR)[0]


def current_period(now: datetime) -> date:
    return period_start_for(now.astimezone(company_tz()).date())


def default_period(now: datetime) -> date:
    """The most recent completed pay period."""
    return current_period(now) - timedelta(weeks=2)


def period_end_for(period_start: date) -> date:
    """The period's last day, the Saturday of its week 2."""
    return period_start + timedelta(days=13)


def approval_deadline_for(period_start: date) -> datetime:
    """When managers should have approved the period: APPROVAL_DEADLINE_DAYS after its last day
    at APPROVAL_DEADLINE_TIME company time, by default Monday 12:00 (D-133)."""
    day = period_end_for(period_start) + timedelta(days=settings.APPROVAL_DEADLINE_DAYS)
    return datetime.combine(day, settings.APPROVAL_DEADLINE_TIME, tzinfo=company_tz())


def period_ended(period_start: date, now: datetime) -> bool:
    """Has the period's last day (Saturday) passed, company time?"""
    return now.astimezone(company_tz()).date() > period_end_for(period_start)


def recent_periods(now: datetime, count: int = 13) -> list[date]:
    """The current period and the `count - 1` before it, newest first."""
    current = current_period(now)
    return [current - timedelta(weeks=2 * i) for i in range(count)]
