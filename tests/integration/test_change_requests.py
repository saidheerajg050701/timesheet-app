from datetime import date, datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.core.exceptions import ValidationError
from django.urls import reverse

from audit.models import AuditLog
from tests.factories import TimeEntryFactory, TimesheetFactory
from tests.forms import brk, form, leave, work
from timesheets.models import ChangeRequest, PeriodApproval, TimeEntry, Timesheet
from timesheets.services.approvals import reject_period
from timesheets.services.changes import raise_request

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)  # fixed_now: Wednesday of the week of Sun 18 Oct
THIS_WEEK = date(2026, 10, 18)
LAST_WEEK = date(2026, 10, 11)  # deadline Sat 17 Oct 12:00 (passed)
TWO_WEEKS_AGO = date(2026, 10, 4)
PERIOD = date(2026, 9, 27)  # pay period: weeks of Sun Sep 27 + Oct 4 (anchor 2026-01-04)
HOOK = "timesheets.services.approvals.supersede_payroll_week"


def monday(week):
    """Entries go on the week's Monday, its first working day (D-114)."""
    return week + timedelta(days=1)


@pytest.fixture
def weeks(org, project, fixed_now):
    """dev1's last week, SUBMITTED on time, plus `make` to add more weeks with one row."""

    def make(employee, week, status, **extra):
        sheet = TimesheetFactory(employee=employee, week_start=week, status=status, **extra)
        TimeEntryFactory(timesheet=sheet, work_date=monday(week), project=project)
        return sheet

    on_time = datetime(2026, 10, 16, 16, 0, tzinfo=TZ)
    return {
        "last": make(org.dev1, LAST_WEEK, "SUBMITTED", submitted_at=on_time),
        "make": make,
    }


def raise_as(login_as, employee, week, reason="Thursday's training is missing."):
    client = login_as(employee)
    response = client.post(reverse("request_change", args=[week]), {"reason": reason})
    return response, ChangeRequest.objects.filter(timesheet__employee=employee).last()


def act(client, change, action, note=""):
    url = reverse("request_detail", args=[change.pk])
    return client.post(url, {"action": action, "note": note})


def test_request_is_visible_to_own_manager_only(org, weeks, login_as):
    """T-23: an employee's change request is visible to their own manager only."""
    response, change = raise_as(login_as, org.dev1, LAST_WEEK)
    assert response.status_code == 302 and change.status == "OPEN"

    inbox = login_as(org.manager).get(reverse("request_inbox")).content.decode()
    assert f'data-request="{change.pk}"' in inbox
    for other in (org.director, org.ops_manager, org.hr):  # higher manager, peer, admin
        html = login_as(other).get(reverse("request_inbox")).content.decode()
        assert f'data-request="{change.pk}"' not in html, other.employee_code
        assert login_as(other).get(reverse("request_detail", args=[change.pk])).status_code == 403
    assert login_as(org.dev1).get(reverse("request_inbox")).status_code == 403


def test_unlock_reopens_until_later_of_48h_and_deadline(org, weeks, login_as, project):
    """T-24: unlock → REOPENED until the later of +48 h and Saturday 12:00; then LOCKED."""
    _, change = raise_as(login_as, org.dev1, LAST_WEEK)
    assert act(login_as(org.manager), change, "unlock").status_code == 302
    sheet = Timesheet.objects.get(pk=weeks["last"].pk)
    assert sheet.status == "REOPENED"
    assert sheet.reopen_until == NOW + timedelta(hours=48)  # later than last Saturday's deadline

    client = login_as(org.dev1)
    url = reverse("timesheet_week", args=[LAST_WEEK])
    with time_machine.travel(NOW + timedelta(hours=47, minutes=59), tick=False):
        assert 'value="save"' in client.get(url).content.decode()
    with time_machine.travel(NOW + timedelta(hours=48), tick=False):
        page = client.get(url).content.decode()
        assert 'id="week-status">Locked<' in page
        rows = form(work(monday(LAST_WEEK), "09:00", "17:00", project))
        assert client.post(url, rows).status_code == 403


def test_edit_directly_writes_before_and_after(org, weeks, login_as, project):
    """T-25: the manager edits directly → AuditLog UPDATE with before/after times and reasons."""
    _, change = raise_as(login_as, org.dev1, LAST_WEEK)
    rows = form(
        work(monday(LAST_WEEK), "08:30", "12:00", project, reason="Release work"),
        brk(monday(LAST_WEEK), "12:00", "12:30"),
        work(monday(LAST_WEEK), "12:30", "17:00", project, reason="Release work"),
        note="Added the release hours you mentioned.",
    )
    client = login_as(org.manager)
    response = client.post(reverse("request_edit", args=[change.pk]), rows)
    assert response.status_code == 302
    row = AuditLog.objects.get(action=AuditLog.Action.UPDATE, entity_type="Timesheet")
    assert row.actor == org.manager and row.change_request_id == change.pk
    assert row.before["entries"] == [
        {
            "work_date": "2026-10-12",
            "category": "PROJECT",
            "project": "I-001",
            "task": "DEV",  # Change 10: the audit names the task (D-151)
            "start": "09:00",
            "end": "17:00",
            "minutes": 480,
            "reason": "Feature development",
        }
    ]
    assert [(e["start"], e["end"], e["reason"]) for e in row.after["entries"]] == [
        ("08:30", "12:00", "Release work"),
        ("12:00", "12:30", "Lunch break"),
        ("12:30", "17:00", "Release work"),
    ]
    change.refresh_from_db()
    assert change.status == "EDITED" and change.resolution.startswith("Added the release")
    sheet = Timesheet.objects.get(pk=weeks["last"].pk)
    assert sheet.status == "SUBMITTED" and sheet.entries.count() == 3


def test_week_unlocked_on_wednesday_stays_open_until_saturday_noon(org, weeks, login_as, project):
    """T-43: a week unlocked on Wednesday is editable until Saturday 12:00, then LOCKED."""
    this = weeks["make"](org.dev1, THIS_WEEK, "SUBMITTED", submitted_at=NOW)
    _, change = raise_as(login_as, org.dev1, THIS_WEEK)
    act(login_as(org.manager), change, "unlock")
    this.refresh_from_db()
    assert this.reopen_until == datetime(2026, 10, 24, 12, 0, tzinfo=TZ)  # not Fri 10:00
    client = login_as(org.dev1)
    url = reverse("timesheet_week", args=[THIS_WEEK])
    with time_machine.travel(datetime(2026, 10, 24, 11, 59, tzinfo=TZ), tick=False):
        assert 'value="submit"' in client.get(url).content.decode()
    with time_machine.travel(datetime(2026, 10, 24, 12, 0, tzinfo=TZ), tick=False):
        assert 'id="week-status">Locked<' in client.get(url).content.decode()


def test_requests_only_on_submitted_locked_or_approved_weeks(org, weeks, login_as):
    """T-81: refused on DRAFT, NOT_STARTED, REOPENED, future weeks and a second OPEN request."""
    make = weeks["make"]
    make(org.dev2, THIS_WEEK, "DRAFT")  # current draft
    make(org.dev2, LAST_WEEK, "REOPENED", reopen_until=NOW + timedelta(days=1))
    for week in (THIS_WEEK, LAST_WEEK):
        response, change = raise_as(login_as, org.dev2, week)
        assert response.status_code == 403 and change is None
    response, _ = raise_as(login_as, org.manager, THIS_WEEK)  # NOT_STARTED
    assert response.status_code == 403
    future = raise_as(login_as, org.dev2, THIS_WEEK + timedelta(weeks=1))[0]
    assert future.status_code == 404

    make(org.dev2, date(2026, 9, 27), "APPROVED")
    make(org.dev2, date(2026, 9, 20), "DRAFT")  # stored DRAFT, effectively LOCKED
    for week in (date(2026, 9, 27), date(2026, 9, 20), TWO_WEEKS_AGO):  # Oct 4: no timesheet
        response, change = raise_as(login_as, org.dev2, week)
        assert response.status_code == 302 and change.timesheet.week_start == week
    assert Timesheet.objects.get(employee=org.dev2, week_start=TWO_WEEKS_AGO).status == "LOCKED"

    client = login_as(org.dev2)
    again = client.post(reverse("request_change", args=[TWO_WEEKS_AGO]), {"reason": "Again"})
    assert "already has an open change request" in client.get(again.url).content.decode()
    blank = client.post(reverse("request_change", args=[date(2026, 9, 13)]), {"reason": "  "})
    assert "Explain what needs to change" in client.get(blank.url).content.decode()
    assert ChangeRequest.objects.filter(timesheet__employee=org.dev2).count() == 3


def test_who_handles_a_request(org, weeks, login_as):
    """T-82: the direct manager handles; HR handles the CEO's; nobody handles their own."""
    make = weeks["make"]
    make(org.ceo, LAST_WEEK, "SUBMITTED")
    make(org.hr, LAST_WEEK, "SUBMITTED")
    _, ceo_request = raise_as(login_as, org.ceo, LAST_WEEK)
    _, hr_request = raise_as(login_as, org.hr, LAST_WEEK)
    _, dev_request = raise_as(login_as, org.dev1, LAST_WEEK)

    def inbox_of(employee):
        html = login_as(employee).get(reverse("request_inbox")).content.decode()
        return {
            r.pk for r in (ceo_request, hr_request, dev_request) if f'data-request="{r.pk}"' in html
        }

    assert inbox_of(org.hr) == {ceo_request.pk}  # admin, for the no-manager CEO; not own
    assert inbox_of(org.ceo) == {hr_request.pk}  # HR's direct manager; not own
    assert inbox_of(org.manager) == {dev_request.pk}
    assert act(login_as(org.ceo), ceo_request, "reject").status_code == 403  # own request
    assert act(login_as(org.director), dev_request, "unlock").status_code == 403
    assert act(login_as(org.hr), dev_request, "reject").status_code == 403  # dev1 has a manager
    assert act(login_as(org.hr), ceo_request, "reject", "Already correct").status_code == 302
    assert ChangeRequest.objects.get(pk=ceo_request.pk).reviewer == org.hr


def test_each_step_is_audited(org, weeks, login_as, project):
    """T-83: raise, reject, unlock and edit each write one AuditLog row with the right actor."""
    make = weeks["make"]
    make(org.dev1, TWO_WEEKS_AGO, "SUBMITTED")
    make(org.dev1, date(2026, 9, 27), "SUBMITTED")
    _, first = raise_as(login_as, org.dev1, LAST_WEEK)
    _, second = raise_as(login_as, org.dev1, TWO_WEEKS_AGO)
    _, third = raise_as(login_as, org.dev1, date(2026, 9, 27))
    manager = login_as(org.manager)
    act(manager, first, "reject", "Hours look right to me.")
    act(manager, second, "unlock")
    manager.post(
        reverse("request_edit", args=[third.pk]),
        form(work(monday(date(2026, 9, 27)), "09:00", "16:00", project)),
    )

    created = AuditLog.objects.filter(action="CREATE", entity_type="ChangeRequest")
    assert {(r.actor, r.change_request_id) for r in created} == {
        (org.dev1, first.pk),
        (org.dev1, second.pk),
        (org.dev1, third.pk),
    }
    reject = AuditLog.objects.get(action="REJECT")
    assert (reject.actor, reject.change_request_id) == (org.manager, first.pk)
    assert reject.after == {"status": "REJECTED", "resolution": "Hours look right to me."}
    unlock = AuditLog.objects.get(action="UNLOCK")
    assert (unlock.actor, unlock.change_request_id) == (org.manager, second.pk)
    assert unlock.before["status"] == "SUBMITTED" and unlock.after["status"] == "REOPENED"
    edit = AuditLog.objects.get(action="UPDATE", entity_type="Timesheet")
    assert (edit.actor, edit.change_request_id) == (org.manager, third.pk)
    assert (
        edit.before["entries"][0]["end"] == "17:00" and edit.after["entries"][0]["end"] == "16:00"
    )


def test_edit_directly_uses_the_same_rules(org, weeks, login_as, project):
    """T-84: Edit directly refuses overlaps, over-long reasons, Break rules and >24 h (D-49)."""
    _, change = raise_as(login_as, org.dev1, LAST_WEEK)
    client = login_as(org.manager)
    url = reverse("request_edit", args=[change.pk])
    day = monday(LAST_WEEK)
    cases = {
        "overlap": form(work(day, "09:00", "12:00", project), brk(day, "11:30", "12:15")),
        "longer than 255 characters": form(work(day, "09:00", "12:00", project, reason="x" * 256)),
        "only project work can have a project": form(
            {**brk(day, "12:00", "12:30"), "project": str(project.pk)}
        ),
        "a week with only breaks": form(brk(day, "12:00", "12:30")),
        "more than 24 hours": form(work(day, "00:00", "20:00", project), leave(day, "5")),
        "Add at least one entry": form(),
    }
    for message, data in cases.items():
        response = client.post(url, data)
        assert response.status_code == 200, message
        assert message in response.content.decode().replace("&#x27;", "'"), message
    change.refresh_from_db()
    assert change.status == "OPEN"
    assert TimeEntry.objects.filter(timesheet__employee=org.dev1).count() == 1
    assert not AuditLog.objects.filter(action="UPDATE").exists()


@pytest.mark.parametrize("action", ["edit", "unlock"])
def test_changing_an_approved_week_resets_the_period(org, weeks, login_as, project, action):
    """T-85: edit/unlock in an APPROVED period → PENDING, weeks leave APPROVED, payroll hook."""
    make = weeks["make"]
    first = make(org.dev1, PERIOD, "APPROVED")
    second = make(org.dev1, TWO_WEEKS_AGO, "APPROVED")
    approval = PeriodApproval.objects.create(
        employee=org.dev1,
        period_start=PERIOD,
        status="APPROVED",
        approver=org.manager,
        decided_at=NOW,
    )
    _, change = raise_as(login_as, org.dev1, TWO_WEEKS_AGO)
    client = login_as(org.manager)
    with mock.patch(HOOK) as hook:
        if action == "edit":
            rows = form(work(monday(TWO_WEEKS_AGO), "09:00", "15:00", project))
            assert client.post(reverse("request_edit", args=[change.pk]), rows).status_code == 302
        else:
            assert act(client, change, "unlock").status_code == 302
    approval.refresh_from_db()
    first.refresh_from_db()
    second.refresh_from_db()
    assert (
        approval.status == "PENDING" and approval.approver is None and approval.decided_at is None
    )
    assert first.status == "SUBMITTED"
    assert second.status == ("SUBMITTED" if action == "edit" else "REOPENED")
    assert sorted(call.args[0].pk for call in hook.call_args_list) == sorted([first.pk, second.pk])
    audit = AuditLog.objects.get(entity_type="PeriodApproval", action="UPDATE")
    assert audit.before["status"] == "APPROVED" and audit.after == {"status": "PENDING"}


def test_reset_is_all_or_nothing(org, weeks, login_as, project):
    """Helper check: if the payroll hook fails, nothing changes (one transaction, D-10)."""
    make = weeks["make"]
    make(org.dev1, PERIOD, "APPROVED")
    second = make(org.dev1, TWO_WEEKS_AGO, "APPROVED")
    PeriodApproval.objects.create(employee=org.dev1, period_start=PERIOD, status="APPROVED")
    _, change = raise_as(login_as, org.dev1, TWO_WEEKS_AGO)
    client = login_as(org.manager)
    with mock.patch(HOOK, side_effect=RuntimeError("payroll down")), pytest.raises(RuntimeError):
        client.post(
            reverse("request_edit", args=[change.pk]),
            form(work(monday(TWO_WEEKS_AGO), "09:00", "15:00", project)),
        )
    second.refresh_from_db()
    change.refresh_from_db()
    assert second.status == "APPROVED" and change.status == "OPEN"
    assert PeriodApproval.objects.get().status == "APPROVED"
    assert second.entries.get().end_time.hour == 17


def test_reopened_past_week_is_editable_until_window_ends(org, weeks, login_as, project):
    """T-86: an unlocked week from two weeks ago is editable until reopen_until; saves audited."""
    weeks["make"](org.dev1, TWO_WEEKS_AGO, "SUBMITTED")
    _, change = raise_as(login_as, org.dev1, TWO_WEEKS_AGO)
    act(login_as(org.manager), change, "unlock")
    client = login_as(org.dev1)
    url = reverse("timesheet_week", args=[TWO_WEEKS_AGO])
    page = client.get(url).content.decode()
    assert "Reopened by your manager" in page and 'value="save"' in page
    rows = form(work(monday(TWO_WEEKS_AGO), "08:00", "17:00", project, reason="Added early start"))
    assert client.post(url, rows).status_code == 302
    audit = AuditLog.objects.get(action="UPDATE", entity_type="Timesheet")
    assert audit.actor == org.dev1
    assert audit.before["entries"][0]["start"] == "09:00"
    assert audit.after["entries"][0] == {
        "work_date": "2026-10-05",
        "category": "PROJECT",
        "project": "I-001",
        "task": "DEV",  # Change 10: the audit names the task (D-151)
        "start": "08:00",
        "end": "17:00",
        "minutes": 540,
        "reason": "Added early start",
    }
    with time_machine.travel(NOW + timedelta(hours=48), tick=False):
        assert 'id="week-status">Locked<' in client.get(url).content.decode()
        assert client.post(url, rows).status_code == 403


def test_late_flag_is_decided_by_the_first_submission(org, weeks, login_as, project):
    """T-87: a missed week submitted later is late for good; an on-time week stays on time."""
    _, missed = raise_as(login_as, org.dev1, TWO_WEEKS_AGO)  # no timesheet at all
    _, on_time = raise_as(login_as, org.dev1, LAST_WEEK)  # submitted Fri 16 Oct
    manager = login_as(org.manager)
    act(manager, missed, "unlock")
    act(manager, on_time, "unlock")
    client = login_as(org.dev1)
    for week in (TWO_WEEKS_AGO, LAST_WEEK):
        rows = form(work(monday(week), "09:00", "17:00", project), action="submit")
        assert client.post(reverse("timesheet_week", args=[week]), rows).status_code == 302
    missed_week = Timesheet.objects.get(employee=org.dev1, week_start=TWO_WEEKS_AGO)
    on_time_week = Timesheet.objects.get(employee=org.dev1, week_start=LAST_WEEK)
    assert missed_week.status == on_time_week.status == "SUBMITTED"
    assert missed_week.is_late and not on_time_week.is_late
    assert on_time_week.reopen_until is None


def test_open_request_count_in_menu(org, weeks, login_as):
    """T-88: handlers see "Change requests" with their open count; employees don't."""
    weeks["make"](org.dev2, LAST_WEEK, "SUBMITTED")
    raise_as(login_as, org.dev1, LAST_WEEK)
    raise_as(login_as, org.dev2, LAST_WEEK)
    html = login_as(org.manager).get("/").content.decode()
    item = html.split('id="menu-change-requests"')[1].split("</a>")[0]
    assert ">2</span>" in item
    assert 'id="menu-change-requests"' in login_as(org.director).get("/").content.decode()
    assert ">2</span>" not in login_as(org.director).get("/").content.decode()
    assert 'id="menu-change-requests"' not in login_as(org.dev1).get("/").content.decode()


def test_my_requests_page_and_closed_requests(org, weeks, login_as, project):
    """Helper check: /requests/ lists only my requests; handled requests can't be acted on again."""
    weeks["make"](org.dev2, LAST_WEEK, "SUBMITTED")
    _, mine = raise_as(login_as, org.dev1, LAST_WEEK)
    _, theirs = raise_as(login_as, org.dev2, LAST_WEEK)
    manager = login_as(org.manager)
    act(manager, mine, "reject", "Looks fine")
    assert act(manager, mine, "unlock").status_code == 403
    assert manager.get(reverse("request_edit", args=[mine.pk])).status_code == 403
    assert "Looks fine" in manager.get(reverse("request_detail", args=[mine.pk])).content.decode()
    html = login_as(org.dev1).get(reverse("requests")).content.decode()
    assert f'data-request="{mine.pk}"' in html and f'data-request="{theirs.pk}"' not in html
    assert "Looks fine" in html and "Rejected" in html


def test_request_totals_use_the_employees_hours(org, weeks, login_as, project):
    """Helper check: the live summary on Edit directly uses the employee's expected hours."""
    org.dev1.expected_weekly_minutes = 1200
    org.dev1.save()
    _, change = raise_as(login_as, org.dev1, LAST_WEEK)
    client = login_as(org.manager)
    html = client.get(reverse("request_edit", args=[change.pk])).content.decode()
    assert 'id="week-expected">20:00<' in html
    url = reverse("request_totals", args=[change.pk])
    totals = client.post(
        url, form(work(monday(LAST_WEEK), "09:00", "11:30", project))
    ).content.decode()
    assert 'id="week-worked">2:30<' in totals and f'hx-post="{url}"' in totals
    assert TimeEntry.objects.get(timesheet__employee=org.dev1).end_time.hour == 17  # unsaved


def test_edit_directly_without_a_reason(org, weeks, login_as, project):
    """T-189: Edit directly saves a slot with no reason; requests and rejections still need one."""
    _, change = raise_as(login_as, org.dev1, LAST_WEEK)
    day = monday(LAST_WEEK)
    rows = form(work(day, "09:00", "17:30", project, reason=""))
    response = login_as(org.manager).post(reverse("request_edit", args=[change.pk]), rows)
    assert response.status_code == 302
    saved = TimeEntry.objects.get(timesheet=weeks["last"])
    assert (saved.minutes, saved.reason) == (510, "")
    row = AuditLog.objects.get(action=AuditLog.Action.UPDATE, entity_type="Timesheet")
    assert [(e["end"], e["reason"]) for e in row.after["entries"]] == [("17:30", "")]
    html = login_as(org.dev1).get(reverse("timesheet_week", args=[LAST_WEEK])).content.decode()
    panel = html.split(f'id="cell-project-{project.pk}-dev-{day.isoformat()}"')[1].split(
        "</dialog>"
    )[0]
    assert "17:30" in panel and ">Reason<" not in panel  # nothing to show

    with pytest.raises(ValidationError, match="Explain what needs to change"):
        raise_request(org.dev1, TWO_WEEKS_AGO, "   ", now=NOW)
    weeks["make"](org.dev1, PERIOD, "SUBMITTED")
    weeks["make"](org.dev1, TWO_WEEKS_AGO, "SUBMITTED")
    with pytest.raises(ValidationError) as refused:
        reject_period(org.manager, org.dev1, PERIOD, "  ", now=NOW)
    assert any("Write a comment" in message for message in refused.value.messages)
    assert not PeriodApproval.objects.exists()
