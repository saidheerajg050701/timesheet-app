"""Hours worked, Break and Leave per day and per week (D-41).

Hours worked counts only work rows; Break is unpaid (D-39) and leave is shown separately.
"""

from dataclasses import dataclass, field
from datetime import date, time

from apps.timesheets.models import TimeEntry
from apps.timesheets.services.calendar import (
    employed_on,
    expected_minutes_for,
    week_days,
    working_days,
)


@dataclass
class DaySummary:
    day: date
    expected: int = 0
    worked: int = 0
    breaks: int = 0
    leave: int = 0
    first_start: time | None = None
    last_end: time | None = None

    @property
    def total(self):
        return self.worked + self.breaks + self.leave


@dataclass
class WeekSummary:
    days: list = field(default_factory=list)
    expected: int = 0

    @property
    def worked(self):
        return sum(d.worked for d in self.days)

    @property
    def breaks(self):
        return sum(d.breaks for d in self.days)

    @property
    def leave(self):
        return sum(d.leave for d in self.days)


def summarize(entries, employee, week_start):
    """Per-day and week totals for any rows with work_date, category, minutes and times."""
    daily_expected = employee.expected_weekly_minutes / 5
    workdays = set(working_days(week_start))  # Mon–Fri; the weekend ends get none (D-114)
    days = {
        day: DaySummary(
            day,
            expected=round(daily_expected) if day in workdays and employed_on(employee, day) else 0,
        )
        for day in week_days(week_start)
    }
    for entry in entries:
        summary = days.get(entry.work_date)
        if summary is None:
            continue
        if entry.category in TimeEntry.WORK:
            summary.worked += entry.minutes
        elif entry.category == TimeEntry.Category.BREAK:
            summary.breaks += entry.minutes
        elif entry.category in TimeEntry.LEAVE:
            summary.leave += entry.minutes
        if entry.start_time is not None:
            if summary.first_start is None or entry.start_time < summary.first_start:
                summary.first_start = entry.start_time
        if entry.end_time is not None:
            if summary.last_end is None or entry.end_time > summary.last_end:
                summary.last_end = entry.end_time
    return WeekSummary(
        days=list(days.values()), expected=expected_minutes_for(employee, week_start)
    )
