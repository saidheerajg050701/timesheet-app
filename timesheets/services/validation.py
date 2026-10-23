"""Time entry rules (B.9 #9). Every rule runs on the server; browser totals are a convenience."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from timesheets.models import Project, TimeEntry
from timesheets.services.calendar import employed_on

STEP_MINUTES = 15  # B.1 row 17
MAX_DAY_MINUTES = 24 * 60
CATEGORY_LABELS = {  # B.1 row 15
    TimeEntry.Category.PROJECT: "Project work",
    TimeEntry.Category.MEETING: "Meetings",
    TimeEntry.Category.TRAINING: "Training",
    TimeEntry.Category.PTO: "PTO",
    TimeEntry.Category.SICK: "Sick",
    TimeEntry.Category.HOLIDAY: "Holiday",
    TimeEntry.Category.OTHER: "Other",
}


@dataclass(frozen=True)
class EntryData:
    work_date: date
    category: str
    project: Project | None
    minutes: int
    notes: str = ""


def day_label(day):
    return day.strftime("%a %-d %b")


def hours_label(minutes):
    return f"{minutes // 60}:{minutes % 60:02d}"


def validate_entries(employee, week_start, entries):
    """Plain-English problems with `entries` for this employee-week; empty list = valid."""
    errors = []
    week_end = week_start + timedelta(days=6)
    day_totals = defaultdict(int)
    for entry in entries:
        where = f"{day_label(entry.work_date)}, {_row_label(entry)}"
        if entry.minutes <= 0 or entry.minutes % STEP_MINUTES:
            errors.append(f"{where}: use 15-minute steps (e.g. 7.25 or 7:15 hours).")
        if not week_start <= entry.work_date <= week_end:
            errors.append(f"{where}: the date is not in the week of {week_start:%-d %b %Y}.")
        elif not employed_on(employee, entry.work_date):
            errors.append(f"{where}: you were not employed on this day.")  # D-19
        if entry.category == TimeEntry.Category.PROJECT:  # D-18
            if entry.project is None:
                errors.append(f"{where}: project work needs a project.")
            elif not entry.project.active:
                errors.append(f"{where}: project {entry.project.code} is no longer active.")
        elif entry.project is not None:
            errors.append(f"{where}: only project work can have a project.")
        day_totals[entry.work_date] += max(entry.minutes, 0)
    for day, total in sorted(day_totals.items()):
        if total > MAX_DAY_MINUTES:
            errors.append(f"{day_label(day)}: {hours_label(total)} hours is more than 24 hours.")
    return errors


def _row_label(entry):
    if entry.category == TimeEntry.Category.PROJECT and entry.project is not None:
        return entry.project.code
    return CATEGORY_LABELS.get(entry.category, entry.category)
