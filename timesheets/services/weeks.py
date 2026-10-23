"""An employee's own weeks: read, save draft, submit (FR-8).

The only code that writes timesheets in Phase 5. Change requests, unlocking and approvals
arrive in Phases 6 and 7.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum

from audit.models import AuditLog
from audit.services.log import record
from timesheets.models import TimeEntry, Timesheet
from timesheets.services.calendar import (
    NOT_STARTED,
    OUTSIDE_EMPLOYMENT,
    company_tz,
    week_start_for,
    week_state,
)
from timesheets.services.validation import CATEGORY_LABELS, validate_entries

STATUS_LABELS = {
    NOT_STARTED: "Not started",
    OUTSIDE_EMPLOYMENT: "Not employed this week",
    Timesheet.Status.DRAFT: "Draft",
    Timesheet.Status.SUBMITTED: "Submitted",
    Timesheet.Status.LOCKED: "Locked",
    Timesheet.Status.REOPENED: "Reopened",
    Timesheet.Status.APPROVED: "Approved",
}


class WeekLocked(PermissionDenied):
    """The week cannot be changed (submitted, approved, past its deadline, or not open)."""


def load_sheet(employee, week_start):
    return Timesheet.objects.filter(employee=employee, week_start=week_start).first()


def save_week(employee, week_start, entries, *, now, submit=False):
    """Replace the week's entries (save draft) and optionally submit it.

    Raises WeekLocked (403) if the week is not editable, ValidationError with plain-English
    messages if the entries break a rule. Nothing is written in either case.
    """
    state = week_state(employee, week_start, load_sheet(employee, week_start), now)
    if not state.editable:
        label = STATUS_LABELS[state.status].lower()
        raise WeekLocked(f"This week is {label} and can't be changed.")
    errors = validate_entries(employee, week_start, entries)
    if submit and not entries:
        errors.append("Add at least one entry before submitting.")  # D-32
    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        sheet, _ = Timesheet.objects.select_for_update().get_or_create(
            employee=employee, week_start=week_start
        )
        if sheet.status not in (Timesheet.Status.DRAFT, Timesheet.Status.REOPENED):
            raise WeekLocked("This week was submitted meanwhile and can't be changed.")
        sheet.entries.all().delete()
        TimeEntry.objects.bulk_create(
            TimeEntry(
                timesheet=sheet,
                work_date=e.work_date,
                category=e.category,
                project=e.project,
                minutes=e.minutes,
                notes=e.notes,
            )
            for e in entries
        )
        if submit:
            sheet.status = Timesheet.Status.SUBMITTED
            sheet.submitted_at = now
            sheet.is_late = sheet.is_late or now > state.deadline  # stays True once late (D-08)
            sheet.save(update_fields=["status", "submitted_at", "is_late"])
            record(
                AuditLog.Action.SUBMIT,
                "Timesheet",
                sheet.pk,
                actor=employee,
                after={
                    "status": sheet.status,
                    "week_start": week_start,
                    "submitted_at": now,
                    "is_late": sheet.is_late,
                    "total_minutes": sum(e.minutes for e in entries),
                },
            )
    return sheet


# --- reading --------------------------------------------------------------------------


@dataclass
class GridRow:
    index: int
    kind: str  # "PROJECT:<id>" or a category
    label: str
    notes: str = ""
    cells: list = field(default_factory=lambda: [""] * 7)  # hours as text, Monday → Sunday


def kind_of(category, project):
    return f"{category}:{project.pk}" if project else category


def minutes_to_hours_text(minutes):
    """450 → "7.5", 465 → "7.75", 480 → "8"."""
    return f"{minutes / 60:.2f}".rstrip("0").rstrip(".") if minutes else ""


def grid_rows(timesheet):
    """The week's entries as grid rows, one per (category, project)."""
    if timesheet is None:
        return []
    rows = {}
    entries = timesheet.entries.select_related("project").order_by("category", "project__code")
    for entry in entries:
        kind = kind_of(entry.category, entry.project)
        if kind not in rows:
            label = entry.project.code if entry.project else CATEGORY_LABELS[entry.category]
            rows[kind] = GridRow(index=len(rows), kind=kind, label=label, notes=entry.notes)
        offset = (entry.work_date - timesheet.week_start).days
        rows[kind].cells[offset] = minutes_to_hours_text(entry.minutes)
    return list(rows.values())


def my_weeks(employee, now, count=12):
    """The employee's current and last `count - 1` weeks within employment, newest first."""
    current = week_start_for(now.astimezone(company_tz()).date())
    starts = [current - timedelta(weeks=i) for i in range(count)]
    sheets = {
        s.week_start: s
        for s in Timesheet.objects.filter(employee=employee, week_start__in=starts).annotate(
            total_minutes=Sum("entries__minutes")
        )
    }
    weeks = []
    for start in starts:
        state = week_state(employee, start, sheets.get(start), now)
        if state.status != OUTSIDE_EMPLOYMENT:
            sheet = sheets.get(start)
            weeks.append((state, (sheet.total_minutes or 0) if sheet else 0))
    return weeks
