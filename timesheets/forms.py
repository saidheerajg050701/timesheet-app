"""Reading the weekly grid from a POST. The rules themselves live in services/validation.py."""

import re
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from timesheets.models import Project, TimeEntry
from timesheets.services.validation import CATEGORY_LABELS, EntryData, day_label
from timesheets.services.weeks import GridRow

ROW_KEY = re.compile(r"^row-(\d+)-kind$")


@dataclass
class ParsedGrid:
    entries: list = field(default_factory=list)  # EntryData
    rows: list = field(default_factory=list)  # GridRow, as typed, to show the form again
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


def kind_choices(extra_project_ids=()):
    """Options for a row: active projects, then the other categories (D-18)."""
    projects = Project.objects.filter(active=True) | Project.objects.filter(
        pk__in=extra_project_ids
    )
    options = [
        (f"{TimeEntry.Category.PROJECT}:{p.pk}", f"{p.code} {p.name}")
        for p in projects.order_by("code")
    ]
    options += [
        (c, label) for c, label in CATEGORY_LABELS.items() if c != TimeEntry.Category.PROJECT
    ]
    return options


def parse_grid(post, week_start):
    parsed = ParsedGrid()
    projects = {str(p.pk): p for p in Project.objects.all()}
    indexes = sorted(int(m.group(1)) for key in post if (m := ROW_KEY.match(key)))
    seen = set()
    for index in indexes:
        kind = post.get(f"row-{index}-kind", "").strip()
        notes = post.get(f"row-{index}-notes", "").strip()[:255]
        cells = [post.get(f"row-{index}-d{d}", "").strip() for d in range(7)]
        parsed.rows.append(GridRow(index=index, kind=kind, label="", notes=notes, cells=cells))
        if not kind and not any(cells):
            continue  # an unused blank row
        category, project, label = _read_kind(kind, projects)
        if category is None:
            parsed.errors.append(f"Row {index + 1}: choose a project or category.")
            continue
        if kind in seen:
            parsed.errors.append(f"{label}: this row appears twice; use one row per item.")
            continue
        seen.add(kind)
        for offset, text in enumerate(cells):
            day = week_start + timedelta(days=offset)
            try:
                minutes = parse_hours(text)
            except ValueError:
                parsed.errors.append(
                    f"{day_label(day)}, {label}: {text!r} is not a number of hours."
                )
                continue
            if minutes:
                parsed.entries.append(EntryData(day, category, project, minutes, notes))
    return parsed


def _read_kind(kind, projects):
    category, _, project_id = kind.partition(":")
    if category == TimeEntry.Category.PROJECT:
        project = projects.get(project_id)
        return (category, project, project.code) if project else (None, None, "")
    if category in CATEGORY_LABELS and not project_id:
        return category, None, CATEGORY_LABELS[category]
    return None, None, ""


def row_totals(rows):
    """Minutes per day (Monday → Sunday) and for the week, from the grid as typed."""
    per_day = [0] * 7
    for row in rows:
        for offset, text in enumerate(row.cells):
            try:
                per_day[offset] += parse_hours(text)
            except ValueError:
                pass  # reported when saving
    return per_day, sum(per_day)
