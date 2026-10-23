from datetime import date, datetime, timedelta
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
LAST_WEEK = date(2026, 10, 12)


def week_url(week=WEEK, name="timesheet_week"):
    return reverse(name, args=[week])


def grid(project, hours=("8", "8", "8", "8", "8", "", ""), action="save", **extra):
    data = {"row-0-kind": f"PROJECT:{project.pk}", "row-0-notes": "Sprint work", "action": action}
    data.update({f"row-0-d{i}": h for i, h in enumerate(hours)})
    data.update(extra)
    return data


@pytest.fixture
def me(db):
    return EmployeeFactory(hire_date=date(2024, 1, 8))


@pytest.fixture
def client_me(login_as, me, fixed_now):
    return login_as(me)


def test_save_draft_then_submit_before_deadline(client_me, me, project, fixed_now):
    """T-20: save a draft, then submit before the deadline → SUBMITTED, not late."""
    response = client_me.post(week_url(), grid(project))
    assert response.status_code == 302
    sheet = Timesheet.objects.get(employee=me, week_start=WEEK)
    assert sheet.status == "DRAFT" and sheet.entries.count() == 5
    assert "Draft saved." in client_me.get(week_url()).content.decode()

    response = client_me.post(week_url(), grid(project, action="submit"))
    assert response.status_code == 302
    sheet.refresh_from_db()
    assert sheet.status == "SUBMITTED" and not sheet.is_late
    assert sheet.submitted_at == fixed_now
    assert sum(sheet.entries.values_list("minutes", flat=True)) == 5 * 480


def test_employee_cannot_edit_after_submitting(client_me, me, project):
    """T-21: editing a submitted week is forbidden and changes nothing."""
    client_me.post(week_url(), grid(project, action="submit"))
    before = list(TimeEntry.objects.values_list("work_date", "minutes"))
    for action in ("save", "submit"):
        changed = grid(project, hours=("1", "", "", "", "", "", ""), action=action)
        assert client_me.post(week_url(), changed).status_code == 403
    assert list(TimeEntry.objects.values_list("work_date", "minutes")) == before
    page = client_me.get(week_url()).content.decode()
    assert "read-only" in page and 'value="save"' not in page and "disabled" in page


def test_unsubmitted_week_locks_at_deadline_and_counts_as_missed(client_me, me, project):
    """T-22: no submission by Saturday 12:00 → LOCKED and counted as missed."""
    client_me.post(week_url(), grid(project))  # a draft, never submitted
    with time_machine.travel(datetime(2026, 10, 24, 12, 0, tzinfo=TZ), tick=False):
        page = client_me.get(week_url()).content.decode()
        assert 'id="week-status">Locked<' in page and "Missed" in page
        assert client_me.post(week_url(), grid(project, action="submit")).status_code == 403
        listing = client_me.get(reverse("timesheets")).content.decode()
        this_week = listing.split('data-week="2026-10-19"')[1].split("</tr>")[0]
        assert "Locked" in this_week and "Missed" in this_week
    assert Timesheet.objects.get(employee=me, week_start=WEEK).status == "DRAFT"  # D-34


def test_submit_writes_audit_row(client_me, me, project, fixed_now):
    """T-71: submitting writes an AuditLog SUBMIT row with the employee as actor."""
    client_me.post(week_url(), grid(project, action="submit"))
    sheet = Timesheet.objects.get(employee=me)
    row = AuditLog.objects.get(action=AuditLog.Action.SUBMIT)
    assert (row.actor, row.entity_type, row.entity_id) == (me, "Timesheet", str(sheet.pk))
    submitted_at = datetime.fromisoformat(row.after.pop("submitted_at").replace("Z", "+00:00"))
    assert submitted_at == fixed_now
    assert row.after == {
        "status": "SUBMITTED",
        "week_start": "2026-10-19",
        "is_late": False,
        "total_minutes": 2400,
    }


def test_invalid_hours_are_refused_on_the_server(client_me, project):
    """Helper check: data posted straight to the server is still validated; nothing saved."""
    cases = {
        ("0.3", "", "", "", "", "", ""): "15-minute steps",
        ("abc", "", "", "", "", "", ""): "is not a number of hours",
        ("25", "", "", "", "", "", ""): "more than 24 hours",
    }
    for hours, message in cases.items():
        response = client_me.post(week_url(), grid(project, hours=hours))
        assert response.status_code == 200
        assert message in response.content.decode()
    duplicate = grid(project, **{"row-1-kind": f"PROJECT:{project.pk}", "row-1-d1": "1"})
    assert "appears twice" in client_me.post(week_url(), duplicate).content.decode()
    no_kind = {"row-0-kind": "", "row-0-d0": "8", "action": "save"}
    assert "choose a project or category" in client_me.post(week_url(), no_kind).content.decode()
    assert not Timesheet.objects.exists()


def test_empty_week_cannot_be_submitted(client_me):
    """Helper check: Submit needs at least one entry (D-32)."""
    response = client_me.post(week_url(), {"action": "submit"})
    assert "Add at least one entry before submitting." in response.content.decode()
    assert not Timesheet.objects.exists()


def test_weekend_hours_and_hour_formats(client_me, me, project):
    """Helper check: weekend hours can be entered in advance (D-09); 7:30 and 7.5 both work."""
    hours = ("7:30", "7.5", "", "", "", "4", "2.25")
    assert client_me.post(week_url(), grid(project, hours=hours)).status_code == 302
    minutes = dict(TimeEntry.objects.values_list("work_date", "minutes"))
    assert minutes[WEEK] == minutes[WEEK + timedelta(days=1)] == 450
    assert minutes[date(2026, 10, 24)] == 240 and minutes[date(2026, 10, 25)] == 135
    page = client_me.get(week_url()).content.decode()
    assert 'value="7.5"' in page and 'value="2.25"' in page and "Sprint work" in page


def test_only_own_timesheets(login_as, org, project, fixed_now):
    """Helper check: a manager opening a week sees only their own, never a report's."""
    report_sheet = TimesheetFactory(employee=org.dev1, week_start=WEEK)
    TimeEntryFactory(timesheet=report_sheet, project=project, minutes=465, notes="dev1 only")
    client = login_as(org.manager)
    page = client.get(week_url()).content.decode()
    assert "dev1 only" not in page and 'value="7.75"' not in page
    client.post(week_url(), grid(project))
    assert Timesheet.objects.get(employee=org.manager).entries.count() == 5
    assert report_sheet.entries.count() == 1  # untouched


def test_week_url_rules(client_me):
    """Helper check: non-Monday dates redirect; future weeks and impossible dates are 404."""
    response = client_me.get(reverse("timesheet_week", args=[date(2026, 10, 22)]))
    assert response.status_code == 302 and response.url == week_url()
    assert client_me.get(week_url(date(2026, 10, 26))).status_code == 404  # D-33
    assert client_me.get("/timesheets/2026-02-30/").status_code == 404


def test_totals_endpoint_recomputes_without_saving(client_me, project):
    """Helper check: HTMX totals are computed on the server and never save anything."""
    response = client_me.post(week_url(name="timesheet_totals"), grid(project))
    html = response.content.decode()
    assert response.status_code == 200 and 'id="week-total" class="fw-semibold">40:00<' in html
    assert "40:00</span> of 40:00 expected" in html
    assert not Timesheet.objects.exists()


def test_add_row_endpoint(client_me):
    """Helper check: "Add row" returns one empty row with the next index."""
    html = client_me.get(week_url(name="timesheet_row"), {"index": 4}).content.decode()
    assert 'name="row-4-kind"' in html and 'name="row-4-d6"' in html
    assert client_me.get(week_url(name="timesheet_row"), {"index": "x"}).status_code == 404


def test_list_shows_weeks_status_and_late(client_me, me, project):
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


def test_save_week_refuses_locked_weeks_itself(me, project, fixed_now):
    """Helper check: the service refuses locked weeks even if a view forgot to check."""
    entry = EntryData(WEEK, "PROJECT", project, 480)
    save_week(me, WEEK, [entry], now=fixed_now, submit=True)
    with pytest.raises(WeekLocked, match="submitted and can't be changed"):
        save_week(me, WEEK, [entry], now=fixed_now)
    with pytest.raises(WeekLocked, match="locked"):
        save_week(me, LAST_WEEK, [], now=fixed_now)


def test_future_weeks_cannot_be_saved_and_are_never_missed(me, project, fixed_now):
    """Helper check: future weeks are refused by the service and never count as missed (D-33)."""
    next_week = WEEK + timedelta(weeks=1)
    with pytest.raises(WeekLocked):
        save_week(me, next_week, [EntryData(next_week, "PROJECT", project, 480)], now=fixed_now)
    assert not Timesheet.objects.exists()
    state = week_state(me, next_week, None, fixed_now)
    assert not state.editable and not state.is_missed


def test_current_week_submits_with_weekend_hours_before_noon_saturday(client_me, project):
    """Helper check: weekend hours entered in advance, submitted Saturday 11:59 (D-09, D-33)."""
    hours = ("8", "8", "8", "8", "4", "4", "")
    with time_machine.travel(datetime(2026, 10, 24, 11, 59, tzinfo=TZ), tick=False):
        response = client_me.post(week_url(), grid(project, hours=hours, action="submit"))
    assert response.status_code == 302
    sheet = Timesheet.objects.get(week_start=WEEK)
    assert sheet.status == "SUBMITTED" and not sheet.is_late
    assert sheet.entries.filter(work_date=date(2026, 10, 24)).exists()
