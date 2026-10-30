from datetime import date, time

import pytest

from apps.directory.models import Employee
from apps.timesheets.services.validation import EntryData, duration, validate_entries
from tests.factories import ProjectFactory, task

# Since Change 10 the rules read a project's allowed tasks, so the projects are saved (D-151).
pytestmark = pytest.mark.django_db

WEEK = date(2026, 10, 18)  # Sunday: the week runs Sun 18 – Sat 24 Oct (D-111)
TUESDAY = date(2026, 10, 20)
ACTIVE = INACTIVE = DEV = None  # set for every test by the fixture below


@pytest.fixture(autouse=True)
def projects():
    global ACTIVE, INACTIVE, DEV
    ACTIVE = ProjectFactory(number=1, name="Customer Portal")  # allows every task
    INACTIVE = ProjectFactory(number=8, name="Legacy Billing", active=False)
    DEV = task("DEV")


def employee(hire=date(2020, 1, 6), end=None):
    return Employee(hire_date=hire, end_date=end)


def work(start="09:00", end="17:00", day=TUESDAY, category="PROJECT", project="active", **extra):
    """A timed row; minutes = end − start unless given; project work is booked to DEV."""
    project = ACTIVE if project == "active" else project
    start_time, end_time = time.fromisoformat(start), time.fromisoformat(end)
    minutes = extra.pop("minutes", max(duration(start_time, end_time), 0))
    reason = extra.pop("reason", "Feature development")
    extra.setdefault("task", DEV if category == "PROJECT" and project is not None else None)
    return EntryData(day, category, project, minutes, reason, start_time, end_time, **extra)


def brk(start, end, day=TUESDAY, project=None, **extra):
    return work(
        start, end, day=day, category="BREAK", project=project, reason="Lunch break", **extra
    )


def leave(minutes=480, day=TUESDAY, category="PTO", **extra):
    return EntryData(day, category, None, minutes, extra.pop("reason", "Vacation"), **extra)


def errors_for(*entries, who=None):
    return validate_entries(who or employee(), WEEK, list(entries))


def has(errors, text):
    return any(text in e for e in errors)


def test_times_and_hours_must_use_15_minute_steps():
    """T-17: times or leave hours that are not in 15-minute steps are rejected."""
    assert has(errors_for(work("09:10", "17:00")), "15-minute steps")
    assert has(errors_for(work("09:00", "16:50")), "15-minute steps")
    for minutes in (18, 7, 481, 0):
        assert has(errors_for(leave(minutes)), "15-minute steps"), minutes
    assert errors_for(work("09:15", "17:45")) == []
    assert errors_for(leave(465)) == []


def test_day_total_over_24_hours_is_rejected():
    """T-18: a day total over 24 hours (work + break + leave together) is rejected."""
    full = [work("00:00", "16:00"), brk("16:00", "20:00")]
    assert errors_for(*full, leave(240)) == []  # exactly 24:00
    assert errors_for(*full, leave(255)) == ["Tue 20 Oct: 24:15 hours is more than 24 hours."]


def test_date_outside_week_or_inactive_project_is_rejected():
    """T-19: an entry dated outside the week, or on an inactive project, is rejected."""
    assert has(errors_for(work(day=date(2026, 10, 25))), "not in the week")  # next Sunday
    assert has(errors_for(work(day=date(2026, 10, 17))), "not in the week")  # Saturday before
    assert errors_for(work(day=date(2026, 10, 18))) == []  # Sunday is the first day
    assert errors_for(work(day=date(2026, 10, 24))) == []  # Saturday is the last day
    assert has(errors_for(work(project=INACTIVE)), "no longer active")


def test_project_entries_need_a_project_and_others_must_not_have_one():
    """T-67: PROJECT needs an active project; other categories must have none (D-18)."""
    assert has(errors_for(work(project=None)), "needs a project")
    for category in ("MEETING", "TRAINING", "OTHER"):
        assert has(errors_for(work(category=category)), "only project work")
        assert errors_for(work(category=category, project=None)) == []
    for category in ("PTO", "SICK", "HOLIDAY"):
        with_project = EntryData(TUESDAY, category, ACTIVE, 480, "Leave")
        assert has(errors_for(with_project), "only project work")
    assert errors_for(work()) == []


def test_entries_only_within_employment():
    """T-68: entries before hire_date or after end_date are rejected (D-19)."""
    joiner = employee(hire=date(2026, 10, 21))  # Wednesday
    leaver = employee(end=date(2026, 10, 22))  # Thursday
    assert has(errors_for(work(day=TUESDAY), who=joiner), "not employed")
    assert errors_for(work(day=date(2026, 10, 21)), who=joiner) == []
    assert has(errors_for(leave(day=date(2026, 10, 23)), who=leaver), "not employed")
    assert errors_for(work(day=date(2026, 10, 22)), who=leaver) == []


def test_end_must_be_after_start():
    """T-72: end before or equal to start, or off the 15-minute grid, is rejected (D-37)."""
    message = "end time must be after the start time"
    assert has(errors_for(work("17:00", "09:00")), message)
    assert has(errors_for(work("09:00", "09:00")), message)
    assert has(errors_for(brk("13:00", "12:30")), message)
    assert has(errors_for(work("09:05", "09:20")), "15-minute steps")
    assert has(errors_for(work("09:00", "10:00", minutes=90)), "don't match")  # direct callers
    assert errors_for(work("00:00", "23:45")) == []  # latest end on the same day


def test_timed_rows_on_one_day_must_not_overlap():
    """T-73: overlapping timed rows (breaks included) are rejected; back-to-back is fine (D-38)."""
    overlap = errors_for(
        work("09:00", "12:00"), work("11:00", "13:00", category="MEETING", project=None)
    )
    assert overlap == ["Tue 20 Oct: 09:00–12:00 I-001-DEV and 11:00–13:00 Meetings overlap."]
    assert has(errors_for(work("09:00", "17:00"), brk("12:00", "12:30")), "overlap")
    assert has(errors_for(brk("12:00", "13:00"), brk("12:45", "13:15")), "overlap")
    back_to_back = [work("09:00", "12:00"), brk("12:00", "12:30"), work("12:30", "17:00")]
    assert errors_for(*back_to_back) == []
    other_day = work("09:00", "12:00", day=date(2026, 10, 21))
    assert errors_for(work("09:00", "12:00"), other_day) == []


def test_reason_is_limited_to_255_characters():
    """T-74: a reason over 255 characters is rejected; 255 is fine (D-36; optional since D-128)."""
    assert has(errors_for(work(reason="x" * 256)), "longer than 255 characters")
    assert has(errors_for(leave(reason="x" * 256)), "longer than 255 characters")
    assert errors_for(work(reason="x" * 255)) == []


def test_empty_reasons_are_accepted():
    """T-187: no reason, or only spaces, is fine on every kind of row; other rules still apply."""
    for reason in ("", "   "):
        rows = [
            work("09:00", "12:00", reason=reason),
            work("12:30", "13:00", category="MEETING", project=None, reason=reason),
            work("12:00", "12:30", category="BREAK", project=None, reason=reason),
            leave(240, day=date(2026, 10, 21), reason=reason),
        ]
        assert errors_for(*rows) == [], repr(reason)
    off_step = errors_for(work("09:10", "12:00", reason=""))
    assert len(off_step) == 1 and "15-minute steps" in off_step[0]
    overlap = errors_for(work("09:00", "12:00", reason=""), brk("11:30", "12:15"))
    assert overlap == ["Tue 20 Oct: 09:00–12:00 I-001-DEV and 11:30–12:15 Break time overlap."]
    assert not has(off_step + overlap, "reason")


def test_break_has_times_and_never_a_project():
    """T-75: a Break with a project, or without times, is rejected (D-39)."""
    assert has(errors_for(brk("12:00", "12:30", project=ACTIVE)), "only project work")
    no_times = EntryData(TUESDAY, "BREAK", None, 30, "Lunch break")
    assert has(errors_for(no_times), "needs a start and an end time")
    assert errors_for(brk("12:00", "12:30")) == []


def test_leave_is_hours_only_and_work_needs_times():
    """T-76: PTO/Sick/Holiday with times are rejected; work rows without times too (D-37, D-40)."""
    for category in ("PTO", "SICK", "HOLIDAY"):
        timed = leave(category=category, start_time=time(9), end_time=time(17))
        assert has(errors_for(timed), "hours only")
        assert has(errors_for(leave(category=category, start_time=time(9))), "hours only")
        assert errors_for(leave(category=category)) == []
    untimed = EntryData(TUESDAY, "MEETING", None, 60, "Client meeting")
    assert has(errors_for(untimed), "needs a start and an end time")
