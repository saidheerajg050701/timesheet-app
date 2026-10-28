"""Change or delete a whole row of the weekly grid (Change 7, D-129, D-130).

These work on the week as typed (the posted EntryRow slots and grid-row keys) and return it
changed. Nothing is saved here: Save draft / Submit (save_week) and Edit directly
(edit_directly) still check every entry rule and write the audit row when the week is saved.
"""

from dataclasses import dataclass

from django.core.exceptions import ValidationError

from timesheets.forms import CATEGORY_GROUPS, split_row_key
from timesheets.models import Project, Task, TimeEntry
from timesheets.services.tasks import task_problem
from timesheets.services.validation import CATEGORY_LABELS


@dataclass
class RowResult:
    rows: list  # EntryRow, every posted slot after the change
    keys: list  # (category, project, task) rows to show even without slots
    slots: int  # filled slots moved or removed
    merged: bool = False  # the target row was already in the grid
    target: tuple = ()  # the row the slots moved to


def split_key(text):
    """ "PROJECT:3:DEV" → ("PROJECT", "3", "DEV"); "MEETING:" → ("MEETING", "", "")."""
    return split_row_key(text)


def normalized(category, project, task):
    """Only project work has a project and a task."""
    if category == TimeEntry.Category.PROJECT:
        return category, project, task
    return category, "", ""


def target_problem(category, project, task=""):
    """Why (category, project, task) can't be a new grid row, or "": the "+ Add row" rule too
    (D-18, D-151) — an active project and one of its allowed, active tasks."""
    if category not in CATEGORY_LABELS:
        return "Choose a category."
    if category != TimeEntry.Category.PROJECT:
        return ""
    found = Project.objects.filter(pk=project, active=True).first() if project.isdigit() else None
    if found is None:
        return "Choose an active project."
    problem = task_problem(found, Task.objects.filter(code=task).first() if task else None)
    return problem[:1].upper() + problem[1:] if problem else ""


def same_kind(source, target):
    """Rows with times (work, Break) change among themselves, leave rows among leave (D-130)."""
    return (source in TimeEntry.TIMED) == (target in TimeEntry.TIMED)


def target_groups(category):
    """The "Change project, task or category" choices for a row of `category`, grouped as in
    "+ Add row": work and Break rows get Work and Break, leave rows get Leave."""
    return [
        (group, options) for group, options in CATEGORY_GROUPS if same_kind(category, options[0][0])
    ]


def _slots(rows, key):
    return [r for r in rows if not r.is_blank and (r.category, r.project, r.task) == key]


def change_row(rows, keys, source, target):
    """Move every slot of row `source` to `target`; dates, times, hours and reasons stay.

    A target that already has a row merges into it (D-130); the save checks overlaps as always.
    """
    target = normalized(*target)
    category, project, task = target
    problem = target_problem(category, project, task)
    if problem:
        raise ValidationError(problem)
    if source[0] not in CATEGORY_LABELS:
        raise ValidationError("Choose a row of this week.")
    if not same_kind(source[0], category):
        raise ValidationError(
            "Leave is entered in hours, without start and end times: a leave row can only "
            "change to another kind of leave, and a work or Break row only to work or Break."
        )
    moving = _slots(rows, source)
    merged = target != source and (bool(_slots(rows, target)) or target in keys)
    for row in moving:
        row.category, row.project, row.task = category, project, task
    keys = [k for k in keys if k != source]
    if target not in keys:
        keys.append(target)
    return RowResult(rows, keys, len(moving), merged, target)


def delete_row(rows, keys, source):
    """Remove row `source` and all its slots from this week as typed."""
    removed = {r.index for r in _slots(rows, source)}
    kept = [r for r in rows if r.index not in removed]
    return RowResult(kept, [k for k in keys if k != source], len(removed))
