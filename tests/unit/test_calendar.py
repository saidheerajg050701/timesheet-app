from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from timesheets.services.calendar import deadline_for, pay_period_for, week_start_for

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
