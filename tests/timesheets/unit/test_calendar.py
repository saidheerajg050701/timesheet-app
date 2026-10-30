from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from apps.directory.models import Employee
from apps.timesheets.checks import pay_period_anchor_is_a_sunday
from apps.timesheets.models import Timesheet
from apps.timesheets.services.calendar import (
    NOT_STARTED,
    OUTSIDE_EMPLOYMENT,
    deadline_for,
    effective_status,
    expected_minutes_for,
    pay_period_for,
    week_days,
    week_start_for,
    week_state,
    working_days,
)

TZ = ZoneInfo("America/Chicago")
ANCHOR = date(2026, 1, 4)  # a Sunday (D-113)


def test_deadline_is_saturday_noon_local():
    """Helper check: deadline_for returns Saturday 12:00 local time."""
    assert deadline_for(date(2026, 10, 18), TZ) == datetime(2026, 10, 24, 12, 0, tzinfo=TZ)


def test_week_start_for_every_day_is_sunday():
    """T-12: week_start_for on every day of the week gives that week's Sunday (D-111)."""
    sunday = date(2026, 10, 18)
    for offset in range(7):  # Sunday … Saturday
        assert week_start_for(sunday + timedelta(days=offset)) == sunday
    assert week_start_for(date(2026, 10, 25)) == date(2026, 10, 25)
    assert week_start_for(date(2027, 1, 2)) == date(2026, 12, 27)  # Saturday across new year


def test_deadline_stays_noon_local_across_daylight_saving():
    """T-15: weeks with the March and November daylight-saving changes keep a 12:00 deadline."""
    cases = [
        (date(2026, 3, 1), 18),  # the week before DST starts: Saturday 7 Mar is CST (UTC-6)
        (date(2026, 3, 8), 17),  # DST starts on its first day, Sun 8 Mar: Saturday is CDT
        (date(2026, 10, 25), 17),  # Saturday 31 Oct is still CDT (UTC-5)
        (date(2026, 11, 1), 18),  # DST ends on its first day, Sun 1 Nov: Saturday is CST
    ]
    for week_start, utc_hour in cases:
        deadline = deadline_for(week_start, TZ)
        assert deadline.weekday() == 5
        assert (deadline.hour, deadline.minute) == (12, 0)
        assert deadline.astimezone(UTC).hour == utc_hour


def test_pay_period_across_year_boundary():
    """T-16: pay_period_for across a year boundary gives the correct 2-week period."""
    assert pay_period_for(ANCHOR, ANCHOR) == (ANCHOR, ANCHOR, date(2026, 1, 11))
    assert pay_period_for(date(2026, 1, 17), ANCHOR)[0] == ANCHOR  # last day (Sat) of period 1
    assert pay_period_for(date(2026, 1, 18), ANCHOR)[0] == date(2026, 1, 18)
    # Before the anchor (New Year's Day 2026 is a Thursday in the week of 28 Dec 2025)
    assert pay_period_for(date(2026, 1, 1), ANCHOR) == (
        date(2025, 12, 21),
        date(2025, 12, 21),
        date(2025, 12, 28),
    )
    # Into 2027: 1 Jan 2027 is in week 2 of the period starting 20 Dec 2026
    assert pay_period_for(date(2027, 1, 1), ANCHOR) == (
        date(2026, 12, 20),
        date(2026, 12, 20),
        date(2026, 12, 27),
    )


def test_week_still_open_at_1159(draft_sheet_week_of_oct_18):
    """T-13: week still open at Saturday 11:59:59."""
    now = datetime(2026, 10, 24, 11, 59, 59, tzinfo=TZ)
    assert effective_status(draft_sheet_week_of_oct_18, now) == "DRAFT"


def test_week_locked_at_noon(draft_sheet_week_of_oct_18):
    """T-14: week locked at Saturday 12:00:00."""
    now = datetime(2026, 10, 24, 12, 0, 0, tzinfo=TZ)
    assert effective_status(draft_sheet_week_of_oct_18, now) == "LOCKED"


def sheet(status, reopen_until=None, week_start=date(2026, 10, 18)):
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
    week = date(2026, 10, 18)  # Sun 18 … Sat 24 Oct
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
    before = week_state(employee, date(2026, 10, 11), None, now)
    hired = week_state(employee, date(2026, 10, 18), None, now)  # Wed–Fri employed
    leaving = week_state(employee, date(2026, 11, 1), None, now)  # Mon–Tue employed
    after = week_state(employee, date(2026, 11, 8), None, now)
    assert before.status == after.status == OUTSIDE_EMPLOYMENT
    assert not before.is_missed and not after.is_missed
    assert hired.status == leaving.status == "LOCKED"
    assert hired.is_missed and leaving.is_missed
    weekend_only = week_state(person(hire=date(2026, 10, 24)), date(2026, 10, 18), None, now)
    assert weekend_only.status == "LOCKED" and not weekend_only.is_missed


def test_week_state_editability():
    """Helper check: open before the deadline, locked after, future weeks never (D-33)."""
    employee = person(hire=date(2020, 1, 6))
    wednesday = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)
    current = week_state(employee, date(2026, 10, 18), None, wednesday)
    assert current.status == NOT_STARTED and current.editable and not current.is_missed
    assert current.deadline == datetime(2026, 10, 24, 12, 0, tzinfo=TZ)
    assert not week_state(employee, date(2026, 10, 25), None, wednesday).editable  # future
    past = week_state(employee, date(2026, 10, 11), None, wednesday)
    assert past.status == "LOCKED" and not past.editable and past.is_missed
    submitted = week_state(employee, date(2026, 10, 18), sheet("SUBMITTED"), wednesday)
    assert submitted.status == "SUBMITTED" and not submitted.editable


@pytest.mark.django_db
def test_existing_sheet_wins_over_employment_dates(draft_sheet_week_of_oct_18):
    """Helper check: a saved week keeps its own status even if employment dates change later."""
    employee = draft_sheet_week_of_oct_18.employee
    employee.end_date = date(2026, 10, 1)
    state = week_state(
        employee, date(2026, 10, 18), draft_sheet_week_of_oct_18, datetime(2026, 10, 21, tzinfo=TZ)
    )
    assert state.status == "DRAFT"


def test_week_boundaries_saturday_night_and_sunday_midnight():
    """T-168: Saturday 23:59 is the last moment of a week; Sunday 00:00 starts the next (D-111)."""
    saturday_night = datetime(2026, 10, 24, 23, 59, 59, tzinfo=TZ)
    sunday_midnight = datetime(2026, 10, 25, 0, 0, tzinfo=TZ)
    assert week_start_for(saturday_night.date()) == date(2026, 10, 18)
    assert week_start_for(sunday_midnight.date()) == date(2026, 10, 25)
    days = week_days(date(2026, 10, 18))
    assert [d.strftime("%a") for d in days] == ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    assert working_days(date(2026, 10, 18)) == days[1:6]  # Monday–Friday (D-114)
    employee = person(hire=date(2020, 1, 6))
    current = week_state(employee, date(2026, 10, 18), None, saturday_night)
    following = week_state(employee, date(2026, 10, 25), None, sunday_midnight)
    assert current.status == "LOCKED" and current.is_missed  # its deadline was at noon
    assert following.status == NOT_STARTED and following.editable
    assert following.deadline == datetime(2026, 10, 31, 12, 0, tzinfo=TZ)
    assert expected_minutes_for(employee, date(2026, 10, 25)) == 2400  # Mon–Fri, 40 h
    assert expected_minutes_for(person(hire=date(2026, 10, 28)), date(2026, 10, 25)) == 1440


def test_pay_period_anchor_must_be_a_sunday(settings):
    """T-170: a non-Sunday PAY_PERIOD_ANCHOR stops the app with a clear message (D-113)."""
    assert pay_period_anchor_is_a_sunday(None) == []  # 2026-01-04, set for every test
    settings.PAY_PERIOD_ANCHOR = date(2026, 1, 5)
    [error] = pay_period_anchor_is_a_sunday(None)
    assert error.id == "timesheets.E001"
    assert "2026-01-05 is a Monday; it must be a Sunday" in error.msg
    assert "2026-01-04" in error.msg and "PAY_PERIOD_ANCHOR=2026-01-04" in error.hint
    with pytest.raises(ValueError, match="must be a Sunday"):
        pay_period_for(date(2026, 10, 21), date(2026, 1, 5))
    sunday = date(2026, 1, 4)
    for weeks in (-26, -2, 0, 2, 40):  # 14-day periods both ways from the anchor
        start = sunday + timedelta(weeks=weeks)
        assert pay_period_for(start + timedelta(days=13), sunday)[0] == start
        assert pay_period_for(start, sunday)[0].weekday() == 6
