"""Small records and helpers shared by the seeder parts."""

from dataclasses import dataclass, field
from datetime import date, datetime, time

from directory.models import Employee
from timesheets.models import TimeEntry, Timesheet


@dataclass
class _Week:
    employee: Employee
    week_start: date
    status: str
    entries: list = field(default_factory=list)
    submitted_at: datetime | None = None
    is_late: bool = False
    reopen_until: datetime | None = None
    manager_note: str = ""
    unlock: tuple | None = None  # (requested_at, unlocked_at) for a late week
    last_event: datetime | None = None
    sheet: Timesheet | None = None


def _timed(day, category, start_minute, minutes, reason, project=None):
    """A row with start and end times on `day`; minutes = end − start (D-37)."""
    end_minute = start_minute + minutes
    return TimeEntry(
        work_date=day,
        category=category,
        project=project,
        minutes=minutes,
        reason=reason,
        start_time=time(start_minute // 60, start_minute % 60),
        end_time=time(end_minute // 60, end_minute % 60),
    )


def _entry_snapshot(entries):
    return [
        {
            "work_date": e.work_date.isoformat(),
            "category": e.category,
            "project": e.project.code if e.project else None,
            "task": e.task.code if e.task else None,
            "start": e.start_time.strftime("%H:%M") if e.start_time else None,
            "end": e.end_time.strftime("%H:%M") if e.end_time else None,
            "minutes": e.minutes,
            "reason": e.reason,
        }
        for e in entries
    ]
