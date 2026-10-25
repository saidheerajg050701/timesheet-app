from datetime import date, timedelta

from django import template

from timesheets.grid import hours_text, slot_minutes
from timesheets.models import TimeEntry
from timesheets.services.validation import CATEGORY_LABELS, day_label
from timesheets.services.weeks import STATUS_LABELS

register = template.Library()

# Status badges (D-102): every status and flag maps to one tone; theme.css colours each
# tone (soft background, dark text, WCAG AA). Rendered by includes/status_badge.html.
TONES = {
    "NOT_STARTED": "neutral",
    "OUTSIDE_EMPLOYMENT": "neutral",
    "DRAFT": "draft",
    "SUBMITTED": "submitted",
    "REOPENED": "reopened",
    "APPROVED": "approved",
    "LOCKED": "danger",
    "MISSED": "danger",
    "PENDING": "neutral",  # pay period, no decision yet
    "IN_PROGRESS": "neutral",
    "REJECTED": "danger",
    "OPEN": "warning",  # change request waiting for the manager
    "UNLOCKED": "approved",
    "EDITED": "approved",
    "CURRENT": "neutral",  # payroll records
    "EXPORTED": "submitted",
    "PAID": "approved",
    "SUPERSEDED": "neutral",
    "SETTLED": "info",  # a corrected week paid through adjustments (D-118)
    "LATE": "warning",  # flags
    "CHANGE_REQUESTED": "warning",
    "OVERTIME": "info",
    "MISSING": "danger",
    "READ_ONLY": "neutral",
    "NOT_SUBMITTED": "neutral",
}
LABELS = {
    **STATUS_LABELS,
    "MISSED": "Missed",
    "IN_PROGRESS": "In progress",
    "CHANGE_REQUESTED": "Change requested",
    "READ_ONLY": "Read-only",
    "NOT_SUBMITTED": "Not submitted yet",
}


@register.filter
def hm(minutes):
    """Minutes as hours:minutes, e.g. 450 → "7:30"."""
    minutes = int(minutes or 0)
    return f"{minutes // 60}:{minutes % 60:02d}"


@register.filter
def status_label(status):
    """Week statuses as in /timesheets/; anything else in title case ("PAID" → "Paid")."""
    return LABELS.get(status, str(status).replace("_", " ").capitalize())


@register.filter
def status_tone(status):
    return TONES.get(status, "neutral")


@register.filter
def missing_days_label(days):
    """3 → "Missing 3 days" (approval flag)."""
    return f"Missing {days} day{'' if days == 1 else 's'}"


@register.filter
def initials(employee):
    """ "John Kim" → "JK", for the avatar in the top bar."""
    return f"{employee.first_name[:1]}{employee.last_name[:1]}".upper()


@register.filter
def add_days(day, days):
    return day + timedelta(days=int(days))


@register.filter
def zip_with(first, second):
    return list(zip(first, second, strict=False))


@register.filter
def countdown(deadline, now):
    """Time left, as the live countdown shows it: "2 d 3 h 10 min"."""
    minutes = int((deadline - now).total_seconds() // 60)
    if minutes <= 0:
        return "deadline passed"
    days, rest = divmod(minutes, 1440)
    hours, mins = divmod(rest, 60)
    parts = [f"{days} d"] if days else []
    if days or hours:
        parts.append(f"{hours} h")
    parts.append(f"{mins} min")
    return " ".join(parts)


@register.filter
def category_label(category):
    return CATEGORY_LABELS.get(category, category)


@register.filter
def iso_day(value):
    """ "2026-10-20" → "Tue 20 Oct"."""
    try:
        return day_label(date.fromisoformat(value))
    except (TypeError, ValueError):
        return value


@register.filter
def is_timed(category):
    """Work and Break rows: hours come from start and end (D-37)."""
    return category in TimeEntry.TIMED


@register.filter
def slot_hours(row):
    """A grid slot's hours as typed: "3.50" (Change 2)."""
    return hours_text(slot_minutes(row))


@register.filter
def signed_hours(minutes):
    """Signed minutes as hours: 90 → "+1.50", -30 → "−0.50", 0 → "0.00" (adjustments)."""
    minutes = int(minutes or 0)
    sign = "+" if minutes > 0 else "−" if minutes < 0 else ""
    return f"{sign}{abs(minutes) / 60:.2f}"


@register.filter
def hours2(minutes):
    """Minutes as hours with 2 decimals: 450 → "7.50" (payroll, D-64)."""
    return f"{int(minutes or 0) / 60:.2f}"
