from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.urls import reverse

from audit.models import AuditLog
from tests.factories import EmployeeFactory, TimeEntryFactory, TimesheetFactory
from timesheets.models import TimeEntry, Timesheet
from timesheets.services.calendar import week_state
from timesheets.services.validation import EntryData
from timesheets.services.weeks import WeekLocked, save_week

TZ = ZoneInfo("America/Chicago")
WEEK = date(2026, 10, 19)  # fixed_now (Wed 21 Oct 10:00) is in this week
TUESDAY = WEEK + timedelta(days=1)
LAST_WEEK = date(2026, 10, 12)


def week_url(week=WEEK, name="timesheet_week"):
    return reverse(name, args=[week])


def work(day, start, end, project=None, category="PROJECT", reason="Feature development"):
    return {
        "date": day.isoformat(),
        "category": category,
        "project": str(project.pk) if project else "",
        "start": start,
        "end": end,
        "reason": reason,
    }


def brk(day, start, end):
    return work(day, start, end, category="BREAK", reason="Lunch break")


def leave(day, hours, category="PTO", reason="Vacation"):
    return {"date": day.isoformat(), "category": category, "hours": hours, "reason": reason}


def form(*rows, action="save"):
    data = {"action": action}
    for index, row in enumerate(rows):
        data.update({f"entry-{index}-{key}": value for key, value in row.items()})
    return data


def full_week(project):
    """Mon–Fri 09:00–12:00 work, 12:00–12:30 break, 12:30–17:30 work = 40 h worked."""
    rows = []
    for offset in range(5):
        day = WEEK + timedelta(days=offset)
        rows += [
            work(day, "09:00", "12:00", project),
            brk(day, "12:00", "12:30"),
            work(day, "12:30", "17:30", project),
        ]
    return rows


@pytest.fixture
def me(db):
    return EmployeeFactory(hire_date=date(2024, 1, 8))


@pytest.fixture
def client_me(login_as, me, fixed_now):
    return login_as(me)


def test_save_draft_then_submit_before_deadline(client_me, me, project, fixed_now):
    """T-20: save a draft, then submit before the deadline → SUBMITTED, not late."""
    response = client_me.post(week_url(), form(*full_week(project)))
    assert response.status_code == 302
    sheet = Timesheet.objects.get(employee=me, week_start=WEEK)
    assert sheet.status == "DRAFT" and sheet.entries.count() == 15
    assert "Draft saved." in client_me.get(week_url()).content.decode()

    response = client_me.post(week_url(), form(*full_week(project), action="submit"))
    assert response.status_code == 302
    sheet.refresh_from_db()
    assert sheet.status == "SUBMITTED" and not sheet.is_late
    assert sheet.submitted_at == fixed_now
    first = sheet.entries.order_by("work_date", "start_time").first()
    assert (first.start_time, first.end_time, first.minutes) == (time(9), time(12), 180)
    assert first.reason == "Feature development"


def test_employee_cannot_edit_after_submitting(client_me, me, project):
    """T-21: editing a submitted week is forbidden and changes nothing."""
    client_me.post(week_url(), form(*full_week(project), action="submit"))
    before = list(TimeEntry.objects.values_list("work_date", "start_time", "minutes"))
    for action in ("save", "submit"):
        changed = form(work(WEEK, "09:00", "10:00", project), action=action)
        assert client_me.post(week_url(), changed).status_code == 403
    assert list(TimeEntry.objects.values_list("work_date", "start_time", "minutes")) == before
    page = client_me.get(week_url()).content.decode()
    assert "read-only" in page and 'value="save"' not in page and "Lunch break" in page


def test_unsubmitted_week_locks_at_deadline_and_counts_as_missed(client_me, me, project):
    """T-22: no submission by Saturday 12:00 → LOCKED and counted as missed."""
    client_me.post(week_url(), form(*full_week(project)))  # a draft, never submitted
    with time_machine.travel(datetime(2026, 10, 24, 12, 0, tzinfo=TZ), tick=False):
        page = client_me.get(week_url()).content.decode()
        assert 'id="week-status">Locked<' in page and "Missed" in page
        submit = form(*full_week(project), action="submit")
        assert client_me.post(week_url(), submit).status_code == 403
        listing = client_me.get(reverse("timesheets")).content.decode()
        this_week = listing.split('data-week="2026-10-19"')[1].split("</tr>")[0]
        assert "Locked" in this_week and "Missed" in this_week
    assert Timesheet.objects.get(employee=me, week_start=WEEK).status == "DRAFT"  # D-34


def test_submit_writes_audit_row(client_me, me, project, fixed_now):
    """T-71: submitting writes an AuditLog SUBMIT row with the employee as actor."""
    rows = full_week(project)[:-3] + [leave(date(2026, 10, 23), "8")]  # Friday is PTO
    client_me.post(week_url(), form(*rows, action="submit"))
    sheet = Timesheet.objects.get(employee=me)
    row = AuditLog.objects.get(action=AuditLog.Action.SUBMIT)
    assert (row.actor, row.entity_type, row.entity_id) == (me, "Timesheet", str(sheet.pk))
    submitted_at = datetime.fromisoformat(row.after.pop("submitted_at").replace("Z", "+00:00"))
    assert submitted_at == fixed_now
    assert row.after == {
        "status": "SUBMITTED",
        "week_start": "2026-10-19",
        "is_late": False,
        "worked_minutes": 4 * 480,
        "break_minutes": 4 * 30,
        "leave_minutes": 480,
    }


def test_hours_worked_excludes_break_and_leave(client_me, me, project):
    """T-77: Hours worked counts only work rows; Break and Leave are shown separately (D-41)."""
    rows = [
        work(TUESDAY, "08:30", "12:00", project),
        brk(TUESDAY, "12:00", "12:45"),
        work(TUESDAY, "12:45", "14:00", category="MEETING", reason="Client meeting"),
        leave(TUESDAY, "4", category="SICK", reason="Doctor's appointment"),
        work(WEEK, "09:00", "11:00", project),
    ]
    assert client_me.post(week_url(), form(*rows)).status_code == 302
    response = client_me.get(week_url())
    summary = response.context["summary"]
    tuesday = summary.days[1]
    assert (tuesday.worked, tuesday.breaks, tuesday.leave) == (285, 45, 240)
    assert (tuesday.first_start, tuesday.last_end) == (time(8, 30), time(14, 0))
    assert tuesday.expected == 480 and summary.days[5].expected == 0  # Saturday
    assert (summary.worked, summary.breaks, summary.leave, summary.expected) == (405, 45, 240, 2400)
    html = response.content.decode()
    assert 'id="week-worked">6:45<' in html and 'id="week-break">0:45<' in html
    assert 'id="week-leave">4:00<' in html and 'id="week-expected">40:00<' in html
    listing = client_me.get(reverse("timesheets")).content.decode()
    this_week = listing.split('data-week="2026-10-19"')[1].split("</tr>")[0]
    assert "6:45" in this_week and "4:00" in this_week and "7:30" not in this_week


def test_break_only_week_cannot_be_submitted(client_me, project):
    """T-78: a week with only Break rows cannot be submitted (D-43)."""
    breaks = form(brk(TUESDAY, "12:00", "12:30"), brk(WEEK, "12:00", "13:00"), action="submit")
    response = client_me.post(week_url(), breaks)
    assert response.status_code == 200
    assert "a week with only breaks can&#x27;t be submitted" in response.content.decode()
    assert not Timesheet.objects.filter(status="SUBMITTED").exists()
    assert client_me.post(week_url(), {**breaks, "action": "save"}).status_code == 302  # draft OK


def test_many_rows_on_one_day(client_me, me, project):
    """T-79: 20 rows on one day plus other days save and show; only the 24 h rule limits (D-35)."""
    rows = []
    for i in range(20):  # 08:00–18:00 in 30-minute rows, every third one a break
        start = time(8 + i // 2, 30 * (i % 2))
        end = time(8 + (i + 1) // 2, 30 * ((i + 1) % 2))
        if i % 3 == 2:
            rows.append(brk(TUESDAY, f"{start:%H:%M}", f"{end:%H:%M}"))
        else:
            rows.append(
                work(TUESDAY, f"{start:%H:%M}", f"{end:%H:%M}", project, reason=f"Task {i}")
            )
    rows += [work(WEEK, "09:00", "17:00", project), leave(date(2026, 10, 22), "8")]
    assert client_me.post(week_url(), form(*rows)).status_code == 302
    assert TimeEntry.objects.filter(work_date=TUESDAY).count() == 20
    assert TimeEntry.objects.count() == 22
    page = client_me.get(week_url()).content.decode()
    assert page.count('<tr id="row-') == 22 + 2  # + two blank rows
    assert "Task 19" in page

    too_long = form(*rows, leave(TUESDAY, "14.25"))  # 10 h + 14:15 = 24:15 on Tuesday
    response = client_me.post(week_url(), too_long)
    assert "24:15 hours is more than 24 hours" in response.content.decode()
    assert TimeEntry.objects.count() == 22


def test_rows_can_be_removed_from_a_draft(client_me, me, project):
    """Helper check: saving without a row removes it (draft rows can be removed, D-35)."""
    rows = [work(WEEK, "09:00", "12:00", project), brk(WEEK, "12:00", "12:30")]
    client_me.post(week_url(), form(*rows, work(TUESDAY, "09:00", "10:00", project)))
    client_me.post(week_url(), form(*rows))
    assert TimeEntry.objects.count() == 2


def test_rows_are_read_and_checked_on_the_server(client_me, project):
    """Helper check: unreadable rows and broken rules are refused; nothing is saved."""
    cases = {
        "times must look like 08:30": form(work(TUESDAY, "9am", "17:00", project)),
        "choose a day of this week": form(work(date(2026, 11, 2), "09:00", "10:00", project)),
        "choose a category": form({**work(TUESDAY, "09:00", "10:00", project), "category": ""}),
        "unknown project": form({**work(TUESDAY, "09:00", "10:00"), "project": "99999"}),
        "is not a number of hours": form(leave(TUESDAY, "lots")),
        "a reason is required": form(work(TUESDAY, "09:00", "10:00", project, reason="")),
        "overlap": form(work(TUESDAY, "09:00", "12:00", project), brk(TUESDAY, "11:30", "12:15")),
        "hours only": form({**leave(TUESDAY, "4"), "start": "09:00", "end": "13:00"}),
    }
    for message, data in cases.items():
        response = client_me.post(week_url(), data)
        assert response.status_code == 200, message
        assert message in response.content.decode(), message
    assert not Timesheet.objects.exists()


def test_empty_week_cannot_be_submitted(client_me):
    """Helper check: Submit needs at least one entry (D-32)."""
    response = client_me.post(week_url(), {"action": "submit"})
    assert "Add at least one entry before submitting." in response.content.decode()
    assert not Timesheet.objects.exists()


def test_weekend_rows_and_leave_hour_formats(client_me, me, project):
    """Helper check: weekend rows can be entered in advance (D-09); 7:30 and 7.5 both work."""
    rows = [
        leave(WEEK, "7:30"),
        leave(TUESDAY, "7.5", category="HOLIDAY", reason="Public holiday"),
        work(date(2026, 10, 24), "10:00", "14:00", project, reason="Release support"),
    ]
    assert client_me.post(week_url(), form(*rows)).status_code == 302
    minutes = dict(TimeEntry.objects.values_list("work_date", "minutes"))
    assert minutes[WEEK] == minutes[TUESDAY] == 450 and minutes[date(2026, 10, 24)] == 240
    page = client_me.get(week_url()).content.decode()
    assert 'value="7.5"' in page and 'value="10:00"' in page and "Release support" in page


def test_only_own_timesheets(login_as, org, project, fixed_now):
    """Helper check: a manager opening a week sees only their own, never a report's."""
    report_sheet = TimesheetFactory(employee=org.dev1, week_start=WEEK)
    TimeEntryFactory(timesheet=report_sheet, project=project, reason="dev1 only")
    client = login_as(org.manager)
    assert "dev1 only" not in client.get(week_url()).content.decode()
    client.post(week_url(), form(*full_week(project)))
    assert Timesheet.objects.get(employee=org.manager).entries.count() == 15
    assert report_sheet.entries.count() == 1  # untouched


def test_week_url_rules(client_me):
    """Helper check: non-Monday dates redirect; future weeks and impossible dates are 404."""
    response = client_me.get(reverse("timesheet_week", args=[date(2026, 10, 22)]))
    assert response.status_code == 302 and response.url == week_url()
    assert client_me.get(week_url(date(2026, 10, 26))).status_code == 404  # D-33
    assert client_me.get("/timesheets/2026-02-30/").status_code == 404


def test_summary_endpoint_recomputes_without_saving(client_me, project):
    """Helper check: the HTMX day summary is computed on the server and never saves."""
    response = client_me.post(week_url(name="timesheet_totals"), form(*full_week(project)))
    html = response.content.decode()
    assert response.status_code == 200
    assert 'id="week-worked">40:00<' in html and 'id="week-break">2:30<' in html
    assert "hx-post" in html  # stays live after the swap
    assert not Timesheet.objects.exists()


def test_add_row_endpoint(client_me):
    """Helper check: "Add row" returns one empty row, prefilled with the day if given."""
    url = week_url(name="timesheet_row")
    html = client_me.get(url, {"index": 41, "date": "2026-10-20"}).content.decode()
    assert 'name="entry-41-reason"' in html and 'data-index="41"' in html
    assert '<option value="2026-10-20" selected>' in html
    assert (
        " selected>" not in client_me.get(url, {"index": 1, "date": "2030-01-01"}).content.decode()
    )
    assert client_me.get(url, {"index": "x"}).status_code == 404


def test_save_week_refuses_locked_weeks_itself(me, project, fixed_now):
    """Helper check: the service refuses locked weeks even if a view forgot to check."""
    entry = EntryData(WEEK, "PROJECT", project, 480, "Feature development", time(9), time(17))
    save_week(me, WEEK, [entry], now=fixed_now, submit=True)
    with pytest.raises(WeekLocked, match="submitted and can't be changed"):
        save_week(me, WEEK, [entry], now=fixed_now)
    with pytest.raises(WeekLocked, match="locked"):
        save_week(me, LAST_WEEK, [], now=fixed_now)


def test_future_weeks_cannot_be_saved_and_are_never_missed(me, project, fixed_now):
    """Helper check: future weeks are refused by the service and never count as missed (D-33)."""
    next_week = WEEK + timedelta(weeks=1)
    entry = EntryData(next_week, "PROJECT", project, 480, "Planning", time(9), time(17))
    with pytest.raises(WeekLocked):
        save_week(me, next_week, [entry], now=fixed_now)
    assert not Timesheet.objects.exists()
    state = week_state(me, next_week, None, fixed_now)
    assert not state.editable and not state.is_missed


def test_current_week_submits_with_weekend_hours_before_noon_saturday(client_me, project):
    """Helper check: weekend hours entered in advance, submitted Saturday 11:59 (D-09, D-33)."""
    rows = [*full_week(project), work(date(2026, 10, 24), "13:00", "17:00", project)]
    with time_machine.travel(datetime(2026, 10, 24, 11, 59, tzinfo=TZ), tick=False):
        response = client_me.post(week_url(), form(*rows, action="submit"))
    assert response.status_code == 302
    sheet = Timesheet.objects.get(week_start=WEEK)
    assert sheet.status == "SUBMITTED" and not sheet.is_late
    assert sheet.entries.filter(work_date=date(2026, 10, 24)).exists()


def test_list_shows_weeks_status_and_late(client_me, me):
    """Helper check: /timesheets/ lists recent weeks with status, late and missed badges."""
    TimesheetFactory(employee=me, week_start=LAST_WEEK, status="SUBMITTED", is_late=True)
    html = client_me.get(reverse("timesheets")).content.decode()
    assert html.count("<tr data-week=") == 12
    assert 'data-week="2026-10-19"' in html and "Not started" in html
    last_week_row = html.split('data-week="2026-10-12"')[1].split("</tr>")[0]
    assert "Submitted" in last_week_row and "Late" in last_week_row
    assert "You have 10 missed weeks" in html  # the 10 older weeks have no timesheet


@pytest.mark.django_db
def test_list_skips_weeks_before_hire_date(login_as, fixed_now):
    """Helper check: weeks before the hire date are not listed (D-19)."""
    newcomer = EmployeeFactory(hire_date=date(2026, 10, 14))
    html = login_as(newcomer).get(reverse("timesheets")).content.decode()
    assert html.count("<tr data-week=") == 2
