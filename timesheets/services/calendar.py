"""Weeks, deadlines and pay periods (B.9 #1, #2, #4).

Pulled forward from Phase 5 because seed_demo needs them (D-25). effective_status and
expected_minutes_for arrive in Phase 5.
"""

from datetime import date, datetime, time, timedelta

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
