"""The weekly grid (Change 2, D-106–D-110): presentation only.

Rows are one per Project / Category, columns Sun–Sat (D-111), and each cell holds the week's entries
for that row and day as time slots. A slot is still one entry row with the usual
`entry-N-*` fields, so parse_entries, validate_entries, save_week and every hook stay the
only place the rules live. This module only groups rows and places messages on cells.
"""

from dataclasses import dataclass, field
from datetime import date

from timesheets.forms import parse_hours, parse_time
from timesheets.models import Project, TimeEntry
from timesheets.services.calendar import week_days
from timesheets.services.validation import CATEGORY_LABELS, day_label, duration, mentions
from timesheets.services.weeks import EntryRow

ROW_ORDER = ("PROJECT", "MEETING", "TRAINING", "OTHER", "BREAK", "PTO", "SICK", "HOLIDAY")
ROW_LABELS = {**CATEGORY_LABELS, "BREAK": "Break (unpaid)"}


def kind_of(category):
    if category in TimeEntry.WORK:
        return "work"
    return "break" if category == TimeEntry.Category.BREAK else "leave"


def slot_minutes(row):
    """Minutes of one slot as typed: from its times (work, Break) or its hours (leave)."""
    if row.category in TimeEntry.TIMED:
        try:
            start, end = parse_time(row.start), parse_time(row.end)
        except ValueError:
            return 0
        return duration(start, end) if start and end and end > start else 0
    try:
        return parse_hours(row.hours)
    except ValueError:
        return 0


def hours_text(minutes):
    return f"{minutes / 60:.2f}"


@dataclass
class Cell:
    id: str
    day: date
    slots: list = field(default_factory=list)  # EntryRow, in time order
    errors: list = field(default_factory=list)
    label: str = ""  # "PRJ-001 Customer Portal, Mon Oct 19"

    @property
    def minutes(self):
        return sum(slot_minutes(s) for s in self.slots)

    @property
    def hours(self):
        return hours_text(self.minutes) if self.slots else ""

    @property
    def aria_label(self):
        count = len(self.slots)
        slots = f"{count} slot{'' if count == 1 else 's'}" if count else "empty"
        errors = ", has errors" if self.errors else ""
        return f"{self.label}: {self.hours or '0.00'} hours, {slots}{errors}"


@dataclass
class GridRow:
    category: str
    project: str  # project id as text, "" for other categories
    label: str
    cells: list = field(default_factory=list)

    @property
    def key(self):
        return f"{self.category}:{self.project}"

    @property
    def name(self):
        """ "PRJ-001 Customer Portal" — the part before " / Project work"."""
        return self.label.split(" / ")[0]

    @property
    def sub(self):
        """ "/ Project work" for project rows, shown on its own line; "" otherwise."""
        return "/ " + self.label.split(" / ")[1] if " / " in self.label else ""

    @property
    def kind(self):
        return kind_of(self.category)

    @property
    def minutes(self):
        return sum(c.minutes for c in self.cells)


@dataclass
class Grid:
    week_start: date
    days: list
    rows: list
    editable: bool
    errors: list = field(default_factory=list)  # (message, cell id or None) for the summary
    day_errors: dict = field(default_factory=dict)  # day → messages (the 24-hour rule)
    next_index: int = 0

    @property
    def footer(self):
        """(day, worked minutes, errors) per day: work rows only, never Break or leave (D-41)."""
        return [
            (
                day,
                sum(r.cells[i].minutes for r in self.rows if r.kind == "work"),
                self.day_errors.get(day, []),
            )
            for i, day in enumerate(self.days)
        ]

    @property
    def worked(self):
        return sum(minutes for _, minutes, _ in self.footer)

    @property
    def keys(self):
        return {r.key for r in self.rows}

    @property
    def template_slot(self):
        """The empty slot each cell dialog clones for "+ Add time slot" (grid.js fills N)."""
        return EntryRow(index="__INDEX__")


def cell_id(category, project, day):
    return f"cell-{category.lower()}-{project or 0}-{day.isoformat()}"


def row_label(category, project, projects):
    if category != TimeEntry.Category.PROJECT:
        return ROW_LABELS.get(category, category)
    found = projects.get(project)
    name = f"{found.code} {found.name}" if found else "Unknown project"
    return f"{name} / {ROW_LABELS['PROJECT']}"


def build_grid(rows, week_start, *, editable, entries=(), problems=(), messages=(), keys=()):
    """The grid for `rows` (EntryRow: saved, or as posted after a failed save).

    `keys` are extra (category, project) rows to show even without slots. `problems` are
    (EntryRow, problem) pairs from parse_entries; `messages` are rule messages from
    validate_entries / save_week about `entries` — each is shown on the cell(s) it names.
    """
    days = week_days(week_start)
    iso_days = {d.isoformat(): d for d in days}
    slots = [r for r in rows if not r.is_blank]
    wanted = {(r.category, r.project) for r in slots if r.category in ROW_LABELS}
    wanted |= {(c, p) for c, p in keys if c in ROW_LABELS}
    projects = Project.objects.in_bulk([int(p) for _, p in wanted if p.isdigit()])
    projects = {str(pk): project for pk, project in projects.items()}

    def order(key):
        category, project = key
        code = projects[project].code if project in projects else project
        return ROW_ORDER.index(category), code

    grid_rows, cells = [], {}
    for category, project in sorted(wanted, key=order):
        label = row_label(category, project, projects)
        row = GridRow(category, project, label)
        for day in days:
            cell = Cell(cell_id(category, project, day), day, label=f"{label}, {day:%a %b %-d}")
            row.cells.append(cell)
            cells[(category, project, day.isoformat())] = cell
        grid_rows.append(row)
    for slot in sorted(slots, key=lambda s: (s.start, s.hours, s.index)):
        cell = cells.get((slot.category, slot.project, slot.work_date))
        if cell is not None:
            cell.slots.append(slot)

    grid = Grid(week_start, days, grid_rows, editable)
    grid.next_index = max((r.index for r in rows), default=-1) + 1
    for row, problem in problems:
        cell = cells.get((row.category, row.project, row.work_date))
        if cell is None:  # no row or day to show it on (e.g. no category chosen)
            where = f" on {day_label(iso_days[row.work_date])}" if row.work_date in iso_days else ""
            grid.errors.append((f"An entry{where}: {problem}", None))
            continue
        text = f"{cell.label}: {problem}"
        cell.errors.append(text)
        grid.errors.append((text, cell.id))
    for message in messages:
        placed = _place(message, entries, cells, iso_days, grid)
        if not placed:
            grid.errors.append((message, None))
    return grid


def _place(message, entries, cells, iso_days, grid):
    """Put a rule message on the cell(s) of the entries it names; True if it was placed."""
    targets = []
    for entry in entries:
        prefix, span = mentions(entry)
        named = message.startswith(prefix + ":") or (
            span and message.startswith(day_label(entry.work_date) + ":") and span in message
        )
        if named:
            project = str(entry.project.pk) if entry.project else ""
            cell = cells.get((entry.category, project, entry.work_date.isoformat()))
            if cell is not None and cell not in targets:
                targets.append(cell)
    for cell in targets:
        cell.errors.append(message)
    if targets:
        grid.errors.append((message, targets[0].id))
        return True
    for day in iso_days.values():  # the 24-hour rule names only the day
        if message.startswith(day_label(day) + ":"):
            grid.day_errors.setdefault(day, []).append(message)
            grid.errors.append((message, None))
            return True
    return False
