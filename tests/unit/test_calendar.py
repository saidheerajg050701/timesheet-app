from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from directory.models import Employee
from timesheets.models import Timesheet
from timesheets.services.calendar import (
    NOT_STARTED,
    OUTSIDE_EMPLOYMENT,
    deadline_for,
    effective_status,
    expected_minutes_for,
    pay_period_for,
    week_start_for,
    week_state,
)

TZ = ZoneInfo("America/Chicago")
ANCHOR = date(2026, 1, 5)


def test_deadline_is_saturday_noon_local():
    """Helper check: deadline_for returns Saturday 12:00 local time."""
    assert deadline_for(date(2026, 10, 19), TZ) == datetime(2026, 10, 24, 12, 0, tzinfo=TZ)


def test_week_start_for_every_day_is_monday():
    """T-12: week_start_for on each weekday and on Sunday gives the correct Monday."""
    monday = date(2026, 10, 19)
    for offset in range(7):  # Monday … Sunday
        assert week_start_for(monday + timedelta(days=offset)) == monday
    assert week_start_for(date(2026, 10, 26)) == date(2026, 10, 26)
    assert week_start_for(date(2027, 1, 3)) == date(2026, 12, 28)  # Sunday across the new year


def test_deadline_stays_noon_local_across_daylight_saving():
    """T-15: weeks with the March and November daylight-saving changes keep a 12:00 deadline."""
    cases = [
        (date(2026, 3, 2), 18),  # DST starts Sun 8 Mar; Saturday is still CST (UTC-6)
        (date(2026, 3, 9), 17),  # first CDT week (UTC-5)
        (date(2026, 10, 26), 17),  # DST ends Sun 1 Nov; Saturday is still CDT
        (date(2026, 11, 2), 18),  # first CST week
    ]
    for week_start, utc_hour in cases:
        deadline = deadline_for(week_start, TZ)
        assert deadline.weekday() == 5
        assert (deadline.hour, deadline.minute) == (12, 0)
        assert deadline.astimezone(UTC).hour == utc_hour


def test_pay_period_across_year_boundary():
    """T-16: pay_period_for across a year boundary gives the correct 2-week period."""
    assert pay_period_for(ANCHOR, ANCHOR) == (ANCHOR, ANCHOR, date(2026, 1, 12))
    assert pay_period_for(date(2026, 1, 18), ANCHOR)[0] == ANCHOR  # last day of period 1
    assert pay_period_for(date(2026, 1, 19), ANCHOR)[0] == date(2026, 1, 19)
    # Before the anchor (New Year's Day 2026 is a Thursday in the week of 29 Dec 2025)
    assert pay_period_for(date(2026, 1, 1), ANCHOR) == (
        date(2025, 12, 22),
        date(2025, 12, 22),
        date(2025, 12, 29),
    )
    # Into 2027: 1 Jan 2027 is in week 2 of the period starting 21 Dec 2026
    assert pay_period_for(date(2027, 1, 1), ANCHOR) == (
        date(2026, 12, 21),
        date(2026, 12, 21),
        date(2026, 12, 28),
    )


def test_week_still_open_at_1159(draft_sheet_week_of_oct_19):
    """T-13: week still open at Saturday 11:59:59."""
    now = datetime(2026, 10, 24, 11, 59, 59, tzinfo=TZ)
    assert effective_status(draft_sheet_week_of_oct_19, now) == "DRAFT"


def test_week_locked_at_noon(draft_sheet_week_of_oct_19):
    """T-14: week locked at Saturday 12:00:00."""
    now = datetime(2026, 10, 24, 12, 0, 0, tzinfo=TZ)
    assert effective_status(draft_sheet_week_of_oct_19, now) == "LOCKED"


def sheet(status, reopen_until=None, week_start=date(2026, 10, 19)):
    return Timesheet(week_start=week_start, status=status, reopen_until=reopen_until)


def test_reopened_week_locks_when_its_window_ends():
    """Helper check: REOPENED becomes LOCKED at reopen_until (D-08, D-21); others unchanged."""
    until = datetime(2026, 10, 27, 9, 0, tzinfo=TZ)
    reopened = sheet(Timesheet.Status.REOPENED, reopen_until=until)
    assert effective_status(reopened, until - timedelta(seconds=1)) == "REOPENED"
    assert effective_status(reopened, until) == "LOCKED"
    later = datetime(2027, 1, 1, tzinfo=TZ)
    for status in ("SUBMITTED", "APPROVED", "LOCKED"):
        assert effective_status(sheet(status), later) == status


def person(hire=None, end=None, minutes=2400):
    return Employee(hire_date=hire, end_date=end, expected_weekly_minutes=minutes)


def test_expected_minutes_are_prorated_for_partial_weeks():
    """T-69: expected_minutes_for prorates by active weekdays; 0 outside employment (D-19)."""
    week = date(2026, 10, 19)  # Mon 19 … Sun 25 Oct
    assert expected_minutes_for(person(hire=date(2020, 1, 6)), week) == 2400
    assert expected_minutes_for(person(hire=date(2026, 10, 21)), week) == 1440  # Wed–Fri
    assert expected_minutes_for(person(end=date(2026, 10, 20)), week) == 960  # Mon–Tue
    assert (
        expected_minutes_for(person(hire=date(2026, 10, 20), end=date(2026, 10, 22)), week) == 1440
    )
    assert expected_minutes_for(person(hire=date(2026, 10, 21), minutes=1200), week) == 720
    assert expected_minutes_for(person(hire=date(2026, 10, 24)), week) == 0  # starts Saturday
    assert expected_minutes_for(person(hire=date(2026, 11, 2)), week) == 0
    assert expected_minutes_for(person(end=date(2026, 10, 16)), week) == 0


def test_weeks_outside_employment_are_never_missed():
    """T-70: weeks fully outside employment are never missed; partly employed weeks are (D-19)."""
    now = datetime(2026, 11, 20, 9, 0, tzinfo=TZ)
    employee = person(hire=date(2026, 10, 21), end=date(2026, 11, 3))
    before = week_state(employee, date(2026, 10, 12), None, now)
    hired = week_state(employee, date(2026, 10, 19), None, now)  # Wed–Fri employed
    leaving = week_state(employee, date(2026, 11, 2), None, now)  # Mon–Tue employed
    after = week_state(employee, date(2026, 11, 9), None, now)
    assert before.status == after.status == OUTSIDE_EMPLOYMENT
    assert not before.is_missed and not after.is_missed
    assert hired.status == leaving.status == "LOCKED"
    assert hired.is_missed and leaving.is_missed
    weekend_only = week_state(person(hire=date(2026, 10, 24)), date(2026, 10, 19), None, now)
    assert weekend_only.status == "LOCKED" and not weekend_only.is_missed


def test_week_state_editability():
    """Helper check: open before the deadline, locked after, future weeks never (D-33)."""
    employee = person(hire=date(2020, 1, 6))
    wednesday = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)
    current = week_state(employee, date(2026, 10, 19), None, wednesday)
    assert current.status == NOT_STARTED and current.editable and not current.is_missed
    assert current.deadline == datetime(2026, 10, 24, 12, 0, tzinfo=TZ)
    assert not week_state(employee, date(2026, 10, 26), None, wednesday).editable  # future
    past = week_state(employee, date(2026, 10, 12), None, wednesday)
    assert past.status == "LOCKED" and not past.editable and past.is_missed
    submitted = week_state(employee, date(2026, 10, 19), sheet("SUBMITTED"), wednesday)
    assert submitted.status == "SUBMITTED" and not submitted.editable


@pytest.mark.django_db
def test_existing_sheet_wins_over_employment_dates(draft_sheet_week_of_oct_19):
    """Helper check: a saved week keeps its own status even if employment dates change later."""
    employee = draft_sheet_week_of_oct_19.employee
    employee.end_date = date(2026, 10, 1)
    state = week_state(
        employee, date(2026, 10, 19), draft_sheet_week_of_oct_19, datetime(2026, 10, 21, tzinfo=TZ)
    )
    assert state.status == "DRAFT"
