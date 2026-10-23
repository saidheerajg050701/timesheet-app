from datetime import date

from directory.models import Employee
from timesheets.models import Project
from timesheets.services.validation import EntryData, validate_entries

WEEK = date(2026, 10, 19)  # Monday
TUESDAY = date(2026, 10, 20)
ACTIVE = Project(code="PRJ-001", name="Customer Portal", active=True)
INACTIVE = Project(code="PRJ-008", name="Legacy Billing", active=False)


def employee(hire=date(2020, 1, 6), end=None):
    return Employee(hire_date=hire, end_date=end)


def work(day=TUESDAY, minutes=480, category="PROJECT", project=ACTIVE):
    return EntryData(day, category, project, minutes)


def errors_for(*entries, who=None):
    return validate_entries(who or employee(), WEEK, list(entries))


def test_minutes_must_be_whole_15_minute_steps():
    """T-17: minutes that are not a multiple of 15 are rejected."""
    for minutes in (20, 7, 481, 0, -15):
        assert any("15-minute steps" in e for e in errors_for(work(minutes=minutes))), minutes
    for minutes in (15, 30, 465, 480):
        assert errors_for(work(minutes=minutes)) == []


def test_day_total_over_24_hours_is_rejected():
    """T-18: a day total over 24 hours is rejected."""
    full_day = [work(minutes=720), work(minutes=720, category="MEETING", project=None)]
    assert errors_for(*full_day) == []  # exactly 24:00 is allowed
    too_much = [*full_day, work(minutes=15, category="OTHER", project=None)]
    assert errors_for(*too_much) == ["Tue 20 Oct: 24:15 hours is more than 24 hours."]


def test_date_outside_week_or_inactive_project_is_rejected():
    """T-19: an entry dated outside the week, or on an inactive project, is rejected."""
    assert any("not in the week" in e for e in errors_for(work(day=date(2026, 10, 26))))
    assert any("not in the week" in e for e in errors_for(work(day=date(2026, 10, 18))))
    assert errors_for(work(day=date(2026, 10, 25))) == []  # Sunday is in the week
    assert any("no longer active" in e for e in errors_for(work(project=INACTIVE)))


def test_project_entries_need_a_project_and_others_must_not_have_one():
    """T-67: PROJECT needs an active project; other categories must have none (D-18)."""
    assert any("needs a project" in e for e in errors_for(work(project=None)))
    for category in ("MEETING", "TRAINING", "PTO", "SICK", "HOLIDAY", "OTHER"):
        assert any("only project work" in e for e in errors_for(work(category=category)))
        assert errors_for(work(category=category, project=None)) == []
    assert errors_for(work()) == []


def test_entries_only_within_employment():
    """T-68: entries before hire_date or after end_date are rejected (D-19)."""
    joiner = employee(hire=date(2026, 10, 21))  # Wednesday
    leaver = employee(end=date(2026, 10, 22))  # Thursday
    assert any("not employed" in e for e in errors_for(work(day=TUESDAY), who=joiner))
    assert errors_for(work(day=date(2026, 10, 21)), who=joiner) == []
    assert any("not employed" in e for e in errors_for(work(day=date(2026, 10, 23)), who=leaver))
    assert errors_for(work(day=date(2026, 10, 22)), who=leaver) == []
