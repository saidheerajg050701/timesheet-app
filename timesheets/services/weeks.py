"""An employee's own weeks: read, save draft, submit (FR-8, D-35–D-43).

The only code that writes timesheets so far. Change requests, unlocking and approvals
arrive in Phases 6 and 7.
"""

from dataclasses import dataclass
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Sum

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
from timesheets.services.summary import summarize
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
    elif submit and all(e.category == TimeEntry.Category.BREAK for e in entries):
        errors.append(  # D-43
            "Add at least one work or leave entry before submitting; "
            "a week with only breaks can't be submitted."
        )
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
                reason=e.reason.strip(),
                start_time=e.start_time,
                end_time=e.end_time,
            )
            for e in entries
        )
        if submit:
            summary = summarize(entries, employee, week_start)
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
                    "worked_minutes": summary.worked,
                    "break_minutes": summary.breaks,
                    "leave_minutes": summary.leave,
                },
            )
    return sheet


# --- reading --------------------------------------------------------------------------


@dataclass
class EntryRow:
    """One entry row as shown or typed: all values as text (D-35, D-36)."""

    index: int
    work_date: str = ""  # ISO date
    category: str = ""
    project: str = ""  # project id
    start: str = ""  # HH:MM
    end: str = ""
    hours: str = ""
    reason: str = ""
    label: str = ""  # read-only display, e.g. "PRJ-001 Customer Portal"

    @property
    def is_blank(self):
        return not any(
            (
                self.work_date,
                self.category,
                self.project,
                self.start,
                self.end,
                self.hours,
                self.reason,
            )
        )


def minutes_to_hours_text(minutes):
    """450 → "7.5", 465 → "7.75", 480 → "8"."""
    return f"{minutes / 60:.2f}".rstrip("0").rstrip(".") if minutes else ""


def entry_rows(timesheet):
    """The week's entries as rows, by date and start time."""
    if timesheet is None:
        return []
    entries = timesheet.entries.select_related("project").order_by("work_date", "start_time", "pk")
    return [
        EntryRow(
            index=i,
            work_date=e.work_date.isoformat(),
            category=e.category,
            project=str(e.project_id or ""),
            start=e.start_time.strftime("%H:%M") if e.start_time else "",
            end=e.end_time.strftime("%H:%M") if e.end_time else "",
            hours=minutes_to_hours_text(e.minutes),
            reason=e.reason,
            label=f"{e.project.code} {e.project.name}"
            if e.project
            else CATEGORY_LABELS[e.category],
        )
        for i, e in enumerate(entries)
    ]


def my_weeks(employee, now, count=12):
    """The employee's current and last `count - 1` weeks within employment, newest first.

    Each item is (week state, minutes worked, leave minutes); Break is never counted (D-41).
    """
    current = week_start_for(now.astimezone(company_tz()).date())
    starts = [current - timedelta(weeks=i) for i in range(count)]
    sheets = {
        s.week_start: s
        for s in Timesheet.objects.filter(employee=employee, week_start__in=starts).annotate(
            worked=Sum("entries__minutes", filter=Q(entries__category__in=TimeEntry.WORK)),
            leave=Sum("entries__minutes", filter=Q(entries__category__in=TimeEntry.LEAVE)),
        )
    }
    weeks = []
    for start in starts:
        sheet = sheets.get(start)
        state = week_state(employee, start, sheet, now)
        if state.status != OUTSIDE_EMPLOYMENT:
            weeks.append(
                (state, sheet.worked or 0 if sheet else 0, sheet.leave or 0 if sheet else 0)
            )
    return weeks
