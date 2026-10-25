"""Change 3: weeks run Sunday → Saturday, identified by their Sunday (D-111–D-116)."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import time_machine
from django.urls import reverse

from tests.factories import TimesheetFactory
from tests.forms import form, work
from timesheets.models import TimeEntry, Timesheet
from timesheets.services.calendar import (
    deadline_for,
    effective_status,
    expected_minutes_for,
    week_start_for,
    week_state,
)

TZ = ZoneInfo("America/Chicago")
WEEK = date(2026, 10, 18)  # Sun 18 – Sat 24 Oct; deadline Sat 24 Oct 12:00


def at(*args):
    return time_machine.travel(datetime(*args, tzinfo=TZ), tick=False)


def test_deadline_is_on_the_last_day(org, project, login_as):
    """T-169: Saturday is the last day: entries for it go in before noon; at 12:00 it locks."""
    TimesheetFactory(employee=org.dev2, week_start=WEEK, status="DRAFT")
    url = reverse("timesheet_week", args=[WEEK])
    rows = form(
        work(date(2026, 10, 19), "09:00", "17:00", project),
        work(
            date(2026, 10, 24), "13:00", "15:00", project, reason="Weekend release"
        ),  # later today
        action="submit",
    )
    with at(2026, 10, 24, 11, 59, 59):
        client = login_as(org.dev1)
        assert client.post(url, rows).status_code == 302  # D-09: entered in advance
        sheet = Timesheet.objects.get(employee=org.dev1, week_start=WEEK)
        assert sheet.status == "SUBMITTED" and not sheet.is_late
        assert TimeEntry.objects.filter(timesheet=sheet, work_date=date(2026, 10, 24)).exists()
        draft = Timesheet.objects.get(employee=org.dev2)
        assert effective_status(draft, datetime.now(TZ)) == "DRAFT"
    with at(2026, 10, 24, 12, 0):
        client = login_as(org.dev2)
        assert 'id="week-status">Locked<' in client.get(url).content.decode()
        assert client.post(url, rows).status_code == 403
        state = week_state(org.dev2, WEEK, draft, datetime.now(TZ))
        assert state.status == "LOCKED" and state.is_missed
        assert state.deadline == datetime(2026, 10, 24, 12, 0, tzinfo=TZ)


def test_non_sunday_dates_redirect_to_their_week(org, login_as, fixed_now, make_week):
    """T-171: an old Monday link or any other day opens the week (Sunday) that contains it."""
    client = login_as(org.dev1)
    for day in ("2026-10-19", "2026-10-21", "2026-10-24"):  # Monday, Wednesday, Saturday
        response = client.get(f"/timesheets/{day}/")
        assert response.status_code == 302 and response.url == "/timesheets/2026-10-18/", day
    assert client.get("/timesheets/2026-10-12/").url == "/timesheets/2026-10-11/"  # old Monday
    assert client.get("/timesheets/2026-10-18/").status_code == 200
    make_week(org.dev1, date(2026, 10, 11))
    manager = login_as(org.manager)
    team_week = reverse("team_member_week", args=["DEV1", date(2026, 10, 12)])
    assert manager.get(team_week).url == reverse(
        "team_member_week", args=["DEV1", date(2026, 10, 11)]
    )


def test_daylight_saving_week(org, project, login_as):
    """T-172: the week of Sun 1 Nov 2026 (clocks go back that night) keeps its rules."""
    week = date(2026, 11, 1)
    assert week_start_for(date(2026, 11, 1)) == week == week_start_for(date(2026, 11, 7))
    deadline = deadline_for(week, TZ)
    assert deadline == datetime(2026, 11, 7, 12, 0, tzinfo=TZ)
    assert deadline.astimezone(UTC).hour == 18  # CST, UTC-6
    assert deadline_for(date(2026, 10, 25), TZ).astimezone(UTC).hour == 17  # CDT, UTC-5
    assert expected_minutes_for(org.dev1, week) == 2400  # Mon–Fri as usual
    url = reverse("timesheet_week", args=[week])
    with at(2026, 11, 4, 10, 0):
        client = login_as(org.dev1)
        sunday = form(work(date(2026, 11, 1), "09:00", "17:00", project, reason="Cut-over"))
        assert client.post(url, sunday).status_code == 302
        entry = TimeEntry.objects.get(work_date=date(2026, 11, 1))
        assert entry.minutes == 480 and entry.timesheet.week_start == week
    sheet = Timesheet.objects.get(employee=org.dev1, week_start=week)
    assert effective_status(sheet, datetime(2026, 11, 7, 11, 59, 59, tzinfo=TZ)) == "DRAFT"
    assert effective_status(sheet, datetime(2026, 11, 7, 12, 0, tzinfo=TZ)) == "LOCKED"
    assert effective_status(sheet, datetime(2026, 11, 7, 17, 59, 59, tzinfo=UTC)) == "DRAFT"
    with at(2026, 11, 7, 12, 0):
        assert 'id="week-status">Locked<' in login_as(org.dev1).get(url).content.decode()
