from datetime import date, time

from apps.directory.models import Employee
from apps.payroll.services.export import hours
from apps.payroll.services.hours import split_hours
from apps.timesheets.models import TimeEntry
from apps.timesheets.services.calendar import expected_minutes_for
from apps.timesheets.templatetags.timesheet_tags import hours2

WEEK = date(2026, 10, 4)  # Sun 4 – Sat 10 Oct


def row(category, minutes, start=None, end=None):
    return TimeEntry(category=category, minutes=minutes, start_time=start, end_time=end)


def test_overtime_rule():
    """T-103: regular up to (prorated) expected, overtime above; leave separate; Break never."""
    week = [
        row("PROJECT", 1800),
        row("MEETING", 300),
        row("TRAINING", 240),
        row("OTHER", 360),  # worked = 2700
        row("BREAK", 600, time(12), time(22)),  # unpaid: never counted anywhere
        row("PTO", 480),
        row("SICK", 240),
        row("HOLIDAY", 480),
    ]
    split = split_hours(week, 2400)
    assert (split.regular, split.overtime) == (2400, 300)
    assert (split.pto, split.sick, split.holiday) == (480, 240, 480)
    assert split.worked == 2700 and split.total == 2400 + 300 + 480 + 240 + 480

    below = split_hours([row("PROJECT", 1500), row("PTO", 480)], 2400)
    assert (below.regular, below.overtime, below.pto, below.total) == (1500, 0, 480, 1980)
    only_break = split_hours([row("BREAK", 120)], 2400)
    assert only_break.total == 0

    # Partial week (D-19): hired Wednesday → expected 3/5 of 40 h = 24 h.
    joiner = Employee(hire_date=date(2026, 10, 7), expected_weekly_minutes=2400)
    expected = expected_minutes_for(joiner, WEEK)
    assert expected == 1440
    part = split_hours([row("PROJECT", 1620)], expected)
    assert (part.regular, part.overtime) == (1440, 180)

    # Stored as minutes, shown as hours with 2 decimals.
    assert hours(450) == hours2(450) == "7.50" and hours(2400) == "40.00" and hours(5) == "0.08"
