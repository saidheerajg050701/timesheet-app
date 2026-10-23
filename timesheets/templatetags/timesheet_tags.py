from datetime import date, timedelta

from django import template

from timesheets.services.validation import CATEGORY_LABELS, day_label
from timesheets.services.weeks import STATUS_LABELS

register = template.Library()

BADGES = {
    "NOT_STARTED": "text-bg-light border",
    "DRAFT": "text-bg-secondary",
    "SUBMITTED": "text-bg-primary",
    "REOPENED": "text-bg-info",
    "APPROVED": "text-bg-success",
    "LOCKED": "text-bg-danger",
    "OUTSIDE_EMPLOYMENT": "text-bg-light border",
}


@register.filter
def hm(minutes):
    """Minutes as hours:minutes, e.g. 450 → "7:30"."""
    minutes = int(minutes or 0)
    return f"{minutes // 60}:{minutes % 60:02d}"


@register.filter
def status_label(status):
    return STATUS_LABELS.get(status, status)


@register.filter
def status_badge(status):
    return BADGES.get(status, "text-bg-secondary")


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
