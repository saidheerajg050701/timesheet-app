"""Regular / overtime / leave split for one approved week (B.1 row 16, D-64)."""

from dataclasses import dataclass

from timesheets.models import TimeEntry


@dataclass(frozen=True)
class HoursSplit:
    regular: int
    overtime: int
    pto: int
    sick: int
    holiday: int

    @property
    def worked(self):
        return self.regular + self.overtime

    @property
    def total(self):
        return self.regular + self.overtime + self.pto + self.sick + self.holiday


def split_hours(entries, expected):
    """Minutes for one week; `expected` is that week's prorated expected minutes (D-19).

    Worked = Project work, Meetings, Training, Other. Up to `expected` is regular, the rest
    overtime. PTO, Sick and Holiday are separate and never overtime. Break never counts.
    """
    worked = sum(e.minutes for e in entries if e.category in TimeEntry.WORK)
    leave = {category: 0 for category in TimeEntry.LEAVE}
    for entry in entries:
        if entry.category in leave:
            leave[entry.category] += entry.minutes
    regular = min(worked, max(expected, 0))
    return HoursSplit(
        regular=regular,
        overtime=worked - regular,
        pto=leave[TimeEntry.Category.PTO],
        sick=leave[TimeEntry.Category.SICK],
        holiday=leave[TimeEntry.Category.HOLIDAY],
    )
