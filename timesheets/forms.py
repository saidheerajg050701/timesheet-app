"""Reading the entry rows from a POST. The rules themselves live in services/validation.py."""

import re
from dataclasses import dataclass, field
from datetime import time
from decimal import Decimal, InvalidOperation

from timesheets.models import Project, TimeEntry
from timesheets.services.calendar import week_days
from timesheets.services.validation import CATEGORY_LABELS, EntryData, day_label, duration
from timesheets.services.weeks import EntryRow, minutes_to_hours_text

ROW_FIELDS = ("date", "category", "project", "start", "end", "hours", "reason")
ROW_KEY = re.compile(r"^entry-(\d+)-(?:" + "|".join(ROW_FIELDS) + r")$")
CATEGORY_GROUPS = (  # the row's category menu
    ("Work", [(c, CATEGORY_LABELS[c]) for c in ("PROJECT", "MEETING", "TRAINING", "OTHER")]),
    ("Break (unpaid)", [("BREAK", CATEGORY_LABELS["BREAK"])]),
    ("Leave (hours only)", [(c, CATEGORY_LABELS[c]) for c in ("PTO", "SICK", "HOLIDAY")]),
)


@dataclass
class ParsedEntries:
    entries: list = field(default_factory=list)  # EntryData that could be read
    rows: list = field(default_factory=list)  # EntryRow, as typed, to show the form again
    errors: list = field(default_factory=list)


def parse_hours(text):
    """Hours as typed ("7.5", "7.25", "7:30", "") → whole minutes. ValueError if unreadable."""
    text = (text or "").strip()
    if not text:
        return 0
    if ":" in text:
        hours, _, mins = text.partition(":")
        hours, mins = int(hours or 0), int(mins)
        if hours < 0 or not 0 <= mins < 60:
            raise ValueError(text)
        return hours * 60 + mins
    try:
        value = Decimal(text) * 60
    except InvalidOperation:
        raise ValueError(text) from None
    if not value.is_finite() or value < 0 or value != value.to_integral_value():
        raise ValueError(text)
    return int(value)


def parse_time(text):
    """ "HH:MM" (or "HH:MM:SS") → time; None if blank; ValueError if unreadable."""
    text = (text or "").strip()
    return time.fromisoformat(text) if text else None


def project_choices(extra_ids=()):
    """Active projects, plus any already used on this week's rows (shown, then rejected)."""
    projects = Project.objects.filter(active=True) | Project.objects.filter(pk__in=extra_ids)
    return [(str(p.pk), f"{p.code} {p.name}") for p in projects.order_by("code")]


def day_choices(week_start):
    return [(d.isoformat(), day_label(d)) for d in week_days(week_start)]


def parse_entries(post, week_start):
    """Every row in the POST, any number of them (D-35). Completely blank rows are ignored.

    Problems reading a row (unknown day, bad time…) are reported here; the business rules
    are checked by validate_entries when saving.
    """
    parsed = ParsedEntries()
    projects = {str(p.pk): p for p in Project.objects.all()}
    days = {d.isoformat(): d for d in week_days(week_start)}
    indexes = sorted({int(m.group(1)) for key in post if (m := ROW_KEY.match(key))})
    for number, index in enumerate(indexes, start=1):
        values = {name: post.get(f"entry-{index}-{name}", "").strip() for name in ROW_FIELDS}
        row = EntryRow(
            index=index,
            work_date=values["date"],
            category=values["category"],
            project=values["project"],
            start=values["start"],
            end=values["end"],
            hours=values["hours"],
            reason=values["reason"],
        )
        parsed.rows.append(row)
        if row.is_blank:
            continue  # nothing typed: ignored, never validated
        entry, problems = _read_row(row, days, projects)
        if row.category in TimeEntry.TIMED:  # shown again after an error (D-37)
            row.hours = _timed_hours_text(row)
        if problems:
            where = f"Row {number}" + (
                f" ({day_label(days[row.work_date])})" if row.work_date in days else ""
            )
            parsed.errors.extend(f"{where}: {problem}" for problem in problems)
        else:
            parsed.entries.append(entry)
    return parsed


def _timed_hours_text(row):
    """Hours from the row's start and end as typed; "" if they can't be read yet."""
    try:
        start, end = parse_time(row.start), parse_time(row.end)
    except ValueError:
        return ""
    if start is None or end is None or end <= start:
        return ""
    return minutes_to_hours_text(duration(start, end))


def _read_row(row, days, projects):
    problems = []
    work_date = days.get(row.work_date)
    if work_date is None:
        problems.append("choose a day of this week.")
    if row.category not in CATEGORY_LABELS:
        problems.append("choose a category.")
    project = projects.get(row.project) if row.project else None
    if row.project and project is None:
        problems.append("unknown project.")
    try:
        start, end = parse_time(row.start), parse_time(row.end)
    except ValueError:
        start = end = None
        problems.append("times must look like 08:30.")
    minutes = 0
    if row.category in TimeEntry.TIMED:
        if start and end:  # minutes come from the times; typed hours are ignored (D-37)
            minutes = duration(start, end)
    elif row.category in CATEGORY_LABELS:
        try:
            minutes = parse_hours(row.hours)
        except ValueError:
            problems.append(f"{row.hours!r} is not a number of hours.")
    if problems:
        return None, problems
    return EntryData(work_date, row.category, project, minutes, row.reason, start, end), []
