"""Time entry rules (B.9 #9). Every rule runs on the server; browser totals are a convenience."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time, timedelta

from timesheets.models import Project, TimeEntry
from timesheets.services.calendar import employed_on

STEP_MINUTES = 15  # B.1 row 17
MAX_DAY_MINUTES = 24 * 60
MAX_REASON = 255
CATEGORY_LABELS = dict(TimeEntry.Category.choices)  # B.1 row 15


@dataclass(frozen=True)
class EntryData:
    """One row as entered; same attribute names as TimeEntry, so saved rows validate too."""

    work_date: date
    category: str
    project: Project | None
    minutes: int
    reason: str = ""
    start_time: time | None = None
    end_time: time | None = None


def day_label(day):
    return day.strftime("%a %-d %b")


def hours_label(minutes):
    return f"{minutes // 60}:{minutes % 60:02d}"


def minutes_of(clock):
    return clock.hour * 60 + clock.minute


def duration(start, end):
    """Whole minutes from start to end on the same day (D-37)."""
    return minutes_of(end) - minutes_of(start)


def validate_entries(employee, week_start, entries):
    """Plain-English problems with `entries` for this employee-week; empty list = valid."""
    errors = []
    week_end = week_start + timedelta(days=6)
    day_totals = defaultdict(int)
    timed_by_day = defaultdict(list)
    for entry in entries:
        where = describe(entry)
        errors.extend(f"{where}: {problem}" for problem in _row_problems(entry))
        if not week_start <= entry.work_date <= week_end:
            errors.append(f"{where}: the date is not in the week of {week_start:%-d %b %Y}.")
        elif not employed_on(employee, entry.work_date):
            errors.append(f"{where}: you were not employed on this day.")  # D-19
        day_totals[entry.work_date] += max(entry.minutes, 0)
        if _has_valid_times(entry):
            timed_by_day[entry.work_date].append(entry)
    for day in sorted(timed_by_day):  # D-38
        rows = sorted(timed_by_day[day], key=lambda e: e.start_time)
        for earlier, later in zip(rows, rows[1:], strict=False):
            if later.start_time < earlier.end_time:
                errors.append(
                    f"{day_label(day)}: {_span(earlier)} {_label(earlier)} and "
                    f"{_span(later)} {_label(later)} overlap."
                )
    for day, total in sorted(day_totals.items()):  # work + break + leave (D-42)
        if total > MAX_DAY_MINUTES:
            errors.append(f"{day_label(day)}: {hours_label(total)} hours is more than 24 hours.")
    return errors


def _row_problems(entry):
    problems = []
    reason = (entry.reason or "").strip()
    if not reason:
        problems.append("a reason is required.")  # D-36
    elif len(reason) > MAX_REASON:
        problems.append(f"the reason is longer than {MAX_REASON} characters.")
    if entry.category not in CATEGORY_LABELS:
        return [*problems, "unknown category."]

    has_start, has_end = entry.start_time is not None, entry.end_time is not None
    if entry.category in TimeEntry.TIMED:  # D-37
        if not (has_start and has_end):
            problems.append("needs a start and an end time.")
        else:
            if not (_on_step(entry.start_time) and _on_step(entry.end_time)):
                problems.append("use times in 15-minute steps (e.g. 08:00, 08:15).")
            if entry.end_time <= entry.start_time:
                problems.append("the end time must be after the start time (same day).")
            elif entry.minutes != duration(entry.start_time, entry.end_time):
                problems.append("the hours don't match the start and end times.")
    else:  # leave: hours only (D-40)
        if has_start or has_end:
            problems.append("leave is entered in hours only, without start or end times.")
        if entry.minutes <= 0 or entry.minutes % STEP_MINUTES:
            problems.append("use 15-minute steps (e.g. 7.25 or 7:15 hours).")

    if entry.category == TimeEntry.Category.PROJECT:  # D-18
        if entry.project is None:
            problems.append("project work needs a project.")
        elif not entry.project.active:
            problems.append(f"project {entry.project.code} is no longer active.")
    elif entry.project is not None:  # includes Break (D-39)
        problems.append("only project work can have a project.")
    return problems


def _on_step(clock):
    return clock.second == 0 and clock.microsecond == 0 and clock.minute % STEP_MINUTES == 0


def _has_valid_times(entry):
    return (
        entry.category in TimeEntry.TIMED
        and entry.start_time is not None
        and entry.end_time is not None
        and entry.end_time > entry.start_time
    )


def _label(entry):
    if entry.category == TimeEntry.Category.PROJECT and entry.project is not None:
        return entry.project.code
    return CATEGORY_LABELS.get(entry.category, entry.category)


def _span(entry):
    return f"{entry.start_time:%H:%M}–{entry.end_time:%H:%M}"


def describe(entry):
    """E.g. "Tue 20 Oct, PRJ-001 09:00–12:00" — used in every message about a row."""
    text = f"{day_label(entry.work_date)}, {_label(entry)}"
    if entry.start_time is not None and entry.end_time is not None:
        text += f" {_span(entry)}"
    return text


def mentions(entry):
    """The texts that name `entry` in the messages above: its describe() prefix, and the
    "09:00–12:00 PRJ-001" span used in overlap messages (None for leave). The weekly grid uses
    them to show each message on the right cell (D-108); the rules don't."""
    span = f"{_span(entry)} {_label(entry)}" if _has_valid_times(entry) else None
    return describe(entry), span
