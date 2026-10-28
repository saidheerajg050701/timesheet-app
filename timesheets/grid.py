"""The weekly grid (Change 2, D-106–D-110): presentation only.

Rows are one per Project / Category, columns Sun–Sat (D-111), and each cell holds the week's entries
for that row and day as time slots. A slot is still one entry row with the usual
`entry-N-*` fields, so parse_entries, validate_entries, save_week and every hook stay the
only place the rules live. This module only groups rows and places messages on cells.
"""

from dataclasses import dataclass, field
from datetime import date

from timesheets.forms import parse_hours, parse_time
from timesheets.models import Project, Task, TimeEntry
from timesheets.services.calendar import week_days
from timesheets.services.grid_rows import target_groups
from timesheets.services.tasks import charge_code, task_label
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
    def has_reasons(self):
        """Does any slot have a reason? Read-only dialogs show the column only then (D-128)."""
        return any(s.reason.strip() for s in self.slots)

    @property
    def slot_times(self):
        """ "08:00–13:00, 14:00–17:00" (leave: "4.00 h, 3.50 h"): the cell's tooltip (D-127)."""
        return ", ".join(
            f"{s.start}–{s.end}"
            if s.category in TimeEntry.TIMED
            else f"{hours_text(slot_minutes(s))} h"
            for s in self.slots
        )

    @property
    def aria_label(self):
        count = len(self.slots)
        slots = f"{count} slot{'' if count == 1 else 's'}" if count else "empty"
        times = f" ({self.slot_times})" if count > 1 else ""
        errors = ", has errors" if self.errors else ""
        return f"{self.label}: {self.hours or '0.00'} hours, {slots}{times}{errors}"


@dataclass
class GridRow:
    category: str
    project: str  # project id as text, "" for other categories
    label: str  # "PRJ-001 Customer Portal · DEV Development", "Meetings"
    cells: list = field(default_factory=list)
    task: str = ""  # task code; "" for other categories and for history rows (D-152)
    charge_code: str = ""  # "PRJ-001-DEV" (project work only, D-150)

    @property
    def key(self):
        """ "PROJECT:3:DEV"; "PROJECT:3" for history without a task; "MEETING:"."""
        base = f"{self.category}:{self.project}"
        return f"{base}:{self.task}" if self.task else base

    @property
    def name(self):
        """ "PRJ-001 Customer Portal" — the part before " · DEV Development"."""
        return self.label.split(LABEL_SEPARATOR)[0]

    @property
    def sub(self):
        """ "DEV Development" (or "Task not recorded") for project rows, on its own line."""
        parts = self.label.split(LABEL_SEPARATOR)
        return parts[1] if len(parts) > 1 else ""

    @property
    def kind(self):
        return kind_of(self.category)

    @property
    def minutes(self):
        return sum(c.minutes for c in self.cells)

    @property
    def dom_id(self):
        """ "row-project-3-dev", "row-meeting-0": ids of the row's action dialogs (D-129)."""
        return f"row-{self.category.lower()}-{self.project or 0}{_task_part(self.task)}"

    @property
    def slot_count(self):
        return sum(len(c.slots) for c in self.cells)

    @property
    def change_groups(self):
        """What "Change project, task or category" offers this row (D-130)."""
        return target_groups(self.category)


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
        """The empty slot a cell dialog clones for "+ Add another time slot" (grid.js fills N)."""
        return EntryRow(index="__INDEX__")


LABEL_SEPARATOR = " · "


def _task_part(task):
    return f"-{task.lower()}" if task else ""


def cell_id(category, project, day, task=""):
    return f"cell-{category.lower()}-{project or 0}{_task_part(task)}-{day.isoformat()}"


def row_label(category, project, projects, task="", tasks=None):
    """ "PRJ-001 Customer Portal · DEV Development" (history: "… · Task not recorded");
    the category label for everything else (D-150)."""
    if category != TimeEntry.Category.PROJECT:
        return ROW_LABELS.get(category, category)
    found = projects.get(project)
    name = f"{found.code} {found.name}" if found else "Unknown project"
    known = (tasks or {}).get(task)
    shown = task_label(known) if known else (task or task_label(None))
    return f"{name}{LABEL_SEPARATOR}{shown}"


def _lookups(keys):
    """{project id: Project}, {task code: Task} for (category, project, task) keys."""
    projects = Project.objects.in_bulk([int(p) for _, p, _ in keys if p.isdigit()])
    tasks = Task.objects.in_bulk([t for _, _, t in keys if t], field_name="code")
    return {str(pk): project for pk, project in projects.items()}, tasks


def slots_text(category, count):
    """ "1 time slot", "3 time slots"; leave: "1 leave entry", "2 leave entries"."""
    if kind_of(category) == "leave":
        return f"{count} leave {'entry' if count == 1 else 'entries'}"
    return f"{count} time slot{'' if count == 1 else 's'}"


def row_notice(action, source, result):
    """The grid's status line after a row action (D-129, D-130)."""
    target = result.target
    projects, tasks = _lookups([k for k in (source, target) if k])

    def label(key):
        category, project, task = key
        return row_label(category, project, projects, task, tasks)

    slots = slots_text(source[0], result.slots)
    if action == "delete" and not result.slots:
        return f"Deleted {label(source)}."  # an empty row: nothing to save
    if action == "delete":
        return f"Deleted {label(source)} ({slots}). Save to keep this change."
    merged = ", merged with its existing row" if result.merged else ""
    return f"Moved {slots} to {label(target)}{merged}. Save to keep this change."


def build_grid(rows, week_start, *, editable, entries=(), problems=(), messages=(), keys=()):
    """The grid for `rows` (EntryRow: saved, or as posted after a failed save).

    `keys` are extra (category, project, task) rows to show even without slots. `problems` are
    (EntryRow, problem) pairs from parse_entries; `messages` are rule messages from
    validate_entries / save_week about `entries` — each is shown on the cell(s) it names.
    """
    days = week_days(week_start)
    iso_days = {d.isoformat(): d for d in days}
    slots = [r for r in rows if not r.is_blank]
    wanted = {(r.category, r.project, r.task) for r in slots if r.category in ROW_LABELS}
    wanted |= {(c, p, t) for c, p, t in keys if c in ROW_LABELS}
    projects, tasks = _lookups(wanted)

    def order(key):
        category, project, task = key
        code = projects[project].code if project in projects else project
        known = tasks.get(task)
        return ROW_ORDER.index(category), code, (known.sort_order if known else -1), task

    grid_rows, cells = [], {}
    for category, project, task in sorted(wanted, key=order):
        label = row_label(category, project, projects, task, tasks)
        code = charge_code(projects.get(project), tasks.get(task)) if project in projects else ""
        row = GridRow(category, project, label, task=task, charge_code=code)
        for day in days:
            the_id = cell_id(category, project, day, task)
            cell = Cell(the_id, day, label=f"{label}, {day:%a %b %-d}")
            row.cells.append(cell)
            cells[(category, project, task, day.isoformat())] = cell
        grid_rows.append(row)
    for slot in sorted(slots, key=lambda s: (s.start, s.hours, s.index)):
        cell = cells.get((slot.category, slot.project, slot.task, slot.work_date))
        if cell is not None:
            cell.slots.append(slot)

    grid = Grid(week_start, days, grid_rows, editable)
    grid.next_index = max((r.index for r in rows), default=-1) + 1
    for row, problem in problems:
        cell = cells.get((row.category, row.project, row.task, row.work_date))
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
            task = entry.task.code if entry.task else ""
            cell = cells.get((entry.category, project, task, entry.work_date.isoformat()))
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
