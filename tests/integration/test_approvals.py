from datetime import date, datetime, time, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse

from audit.models import AuditLog
from directory.models import Employee
from tests.factories import EmployeeFactory, TimeEntryFactory
from tests.forms import form, work
from timesheets.models import ChangeRequest, PeriodApproval, Timesheet
from timesheets.services.approvals import period_rows
from timesheets.services.calendar import (
    current_period,
    default_period,
    period_start_for,
    recent_periods,
)

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)  # fixed_now: Wed, in the period of Oct 11
PERIOD = date(2026, 9, 27)  # most recent completed period: weeks of Sun Sep 27 + Oct 4
WEEK1, WEEK2 = PERIOD, PERIOD + timedelta(weeks=1)
CURRENT = date(2026, 10, 11)  # current period: weeks of Sun Oct 11 + Oct 18
HOOK = "timesheets.services.approvals.publish_payroll_period"


def detail_url(employee, period=PERIOD):
    return reverse("approval_detail", args=[period, employee.employee_code])


def post(client, employee, action, period=PERIOD, **data):
    return client.post(detail_url(employee, period), {"action": action, **data})


def decision(employee, period=PERIOD):
    return PeriodApproval.objects.filter(employee=employee, period_start=period).first()


def status(employee, week):
    return Timesheet.objects.get(employee=employee, week_start=week).status


def test_approve_blocked_while_a_week_is_draft_or_locked(org, make_week, login_as):
    """T-29: approve is blocked while a week is still DRAFT or LOCKED, with the reason shown."""
    make_week(org.dev1, WEEK1)
    make_week(org.dev1, WEEK2, "LOCKED")
    make_week(org.dev2, CURRENT)
    make_week(org.dev2, CURRENT + timedelta(weeks=1), "DRAFT")
    client = login_as(org.manager)

    page = client.get(detail_url(org.dev1)).content.decode()
    assert "Week 2 is locked — unlock it first." in page and 'value="approve"' not in page
    response = post(client, org.dev1, "approve")
    assert "Week 2 is locked" in client.get(response.url).content.decode()
    page = client.get(detail_url(org.dev2, CURRENT)).content.decode()
    assert "Week 2 hasn&#x27;t been submitted yet." in page
    post(client, org.dev2, "approve", CURRENT)
    assert decision(org.dev1) is None and decision(org.dev2, CURRENT) is None
    assert status(org.dev1, WEEK1) == "SUBMITTED"


def test_approving_both_weeks(org, make_week, login_as):
    """T-30: both weeks SUBMITTED → approve: APPROVED, both weeks APPROVED, audit entry."""
    make_week(org.dev1, WEEK1)
    make_week(org.dev1, WEEK2)
    response = post(login_as(org.manager), org.dev1, "approve")
    assert response.status_code == 302
    approval = decision(org.dev1)
    assert (approval.status, approval.approver, approval.decided_at) == (
        "APPROVED",
        org.manager,
        NOW,
    )
    assert status(org.dev1, WEEK1) == status(org.dev1, WEEK2) == "APPROVED"
    audit = AuditLog.objects.get(action="APPROVE")
    assert (audit.actor, audit.entity_id) == (org.manager, str(approval.pk))
    assert audit.after["worked_minutes"] == 2 * 2400 and audit.after["status"] == "APPROVED"
    assert audit.before["weeks"] == {"2026-09-27": "SUBMITTED", "2026-10-04": "SUBMITTED"}


def test_reject_needs_a_comment_and_reopens_both_weeks(org, make_week, login_as):
    """T-31: reject without a comment is blocked; with one → REOPENED per D-21."""
    make_week(org.dev1, WEEK1)
    make_week(org.dev1, WEEK2)
    client = login_as(org.manager)
    response = post(client, org.dev1, "reject", comment="  ")
    assert "Write a comment" in client.get(response.url).content.decode()
    assert decision(org.dev1) is None and status(org.dev1, WEEK1) == "SUBMITTED"

    post(client, org.dev1, "reject", comment="Tuesday is missing the client call.")
    approval = decision(org.dev1)
    assert approval.status == "REJECTED" and approval.comment.startswith("Tuesday")
    for week in (WEEK1, WEEK2):
        sheet = Timesheet.objects.get(employee=org.dev1, week_start=week)
        assert sheet.status == "REOPENED"
        assert sheet.reopen_until == NOW + timedelta(hours=48)  # later than both deadlines
        assert sheet.manager_note == "Tuesday is missing the client call."
    assert AuditLog.objects.get(action="REJECT").actor == org.manager


def test_non_manager_cannot_approve(org, make_week, login_as):
    """T-32: a non-manager gets 403 on the approvals pages and actions."""
    make_week(org.dev2, WEEK1)
    make_week(org.dev2, WEEK2)
    client = login_as(org.dev1)
    assert client.get(reverse("approvals")).status_code == 403
    assert client.get(detail_url(org.dev2)).status_code == 403
    assert post(client, org.dev2, "approve").status_code == 403
    assert decision(org.dev2) is None


def test_unlock_locked_week_from_approvals(org, make_week, login_as):
    """T-92: Unlock reuses Phase 6: manager-authored UNLOCKED request (or resolves the open one)."""
    make_week(org.dev1, WEEK1)  # week 2 (Oct 4) has no timesheet at all: missed
    client = login_as(org.manager)
    assert "Unlock week 2" in client.get(detail_url(org.dev1)).content.decode()
    post(client, org.dev1, "unlock", week=WEEK2.isoformat())
    sheet = Timesheet.objects.get(employee=org.dev1, week_start=WEEK2)
    assert sheet.status == "REOPENED" and sheet.reopen_until == NOW + timedelta(hours=48)
    request = ChangeRequest.objects.get(timesheet=sheet)
    assert (request.requester, request.status, request.reviewer) == (
        org.manager,
        "UNLOCKED",
        org.manager,
    )
    unlock = AuditLog.objects.get(action="UNLOCK")
    assert (unlock.actor, unlock.change_request) == (org.manager, request)

    # A locked week that already has the employee's open request: that request is resolved.
    locked = make_week(org.dev2, WEEK2, "LOCKED")
    asked = ChangeRequest.objects.create(timesheet=locked, requester=org.dev2, reason="Forgot")
    post(client, org.dev2, "unlock", week=WEEK2.isoformat())
    asked.refresh_from_db()
    assert asked.status == "UNLOCKED" and asked.reviewer == org.manager
    assert ChangeRequest.objects.filter(timesheet=locked).count() == 1

    response = post(client, org.dev1, "unlock", week=WEEK1.isoformat())  # submitted, not locked
    assert "Only a locked week" in client.get(response.url).content.decode()


def test_rejected_period_comes_back_after_resubmission(org, make_week, login_as, project):
    """T-93: the comment reaches the employee; resubmitting makes the period pending again."""
    make_week(org.dev1, WEEK1)
    make_week(org.dev1, WEEK2)
    post(login_as(org.manager), org.dev1, "reject", comment="Add Friday's training.")
    employee = login_as(org.dev1)
    week_page = employee.get(reverse("timesheet_week", args=[WEEK1])).content.decode()
    assert "Add Friday&#x27;s training." in week_page and "Rejected by" in week_page

    rows = [work(WEEK1 + timedelta(days=d), "09:00", "17:00", project) for d in range(1, 6)]
    employee.post(reverse("timesheet_week", args=[WEEK1]), form(*rows, action="submit"))
    assert decision(org.dev1).status == "PENDING"
    audit = AuditLog.objects.get(entity_type="PeriodApproval", action="UPDATE")
    assert audit.actor == org.dev1 and audit.after["status"] == "PENDING"
    manager = login_as(org.manager)
    assert "Week 2 is reopened" in manager.get(detail_url(org.dev1)).content.decode()

    rows = [work(WEEK2 + timedelta(days=d), "09:00", "17:00", project) for d in range(1, 6)]
    login_as(org.dev1).post(reverse("timesheet_week", args=[WEEK2]), form(*rows, action="submit"))
    post(login_as(org.manager), org.dev1, "approve")
    assert decision(org.dev1).status == "APPROVED"


def test_approve_is_one_transaction_with_the_payroll_hook(org, make_week, login_as):
    """T-94: the payroll hook runs inside the approve transaction; a failure undoes everything."""
    make_week(org.dev1, WEEK1)
    make_week(org.dev1, WEEK2)
    client = login_as(org.manager)
    with mock.patch(HOOK, side_effect=RuntimeError("payroll down")), pytest.raises(RuntimeError):
        post(client, org.dev1, "approve")
    assert decision(org.dev1) is None
    assert status(org.dev1, WEEK1) == status(org.dev1, WEEK2) == "SUBMITTED"
    assert not AuditLog.objects.filter(action="APPROVE").exists()

    with mock.patch(HOOK) as hook:
        post(client, org.dev1, "approve")
    hook.assert_called_once()
    assert hook.call_args.args[0] == decision(org.dev1)
    assert hook.call_args.kwargs == {"actor": org.manager, "at": NOW}


def test_who_sees_and_approves_which_rows(org, make_week, login_as):
    """T-95: direct reports only; admins also get no-manager employees; never yourself."""
    for person in (org.ceo, org.hr, org.director, org.manager, org.dev1, org.dev2, org.ops1):
        make_week(person, WEEK1)
        make_week(person, WEEK2)

    def rows_for(viewer):
        html = login_as(viewer).get(reverse("approvals")).content.decode()
        return {
            e.employee_code
            for e in Employee.objects.all()
            if f'data-employee="{e.employee_code}"' in html
        }

    assert rows_for(org.manager) == {"DEV1", "DEV2"}
    assert rows_for(org.director) == {"MANAGER"}  # not the indirect reports
    assert rows_for(org.hr) == {"CEO"}  # admin: the no-manager CEO, never HR itself
    assert rows_for(org.ceo) == {"HR", "DIRECTOR", "OPSMGR", "FINANCE"}  # never the CEO
    assert login_as(org.ceo).get(detail_url(org.ceo)).status_code == 403
    assert post(login_as(org.director), org.dev1, "approve").status_code == 403
    assert post(login_as(org.hr), org.ceo, "approve").status_code == 302
    assert decision(org.ceo).approver == org.hr


def test_bulk_approve(org, make_week, login_as):
    """T-96: only clean rows can be ticked; ineligible ones are skipped with a reason."""
    make_week(org.dev1, WEEK1)
    make_week(org.dev1, WEEK2)
    make_week(org.dev2, WEEK1, is_late=True)  # flagged: late
    make_week(org.dev2, WEEK2)
    client = login_as(org.manager)
    html = client.get(reverse("approvals")).content.decode()
    assert 'name="employee" value="DEV1"' in html and 'name="employee" value="DEV2"' not in html

    data = {"period": PERIOD.isoformat(), "employee": ["DEV1", "DEV2", "OPS1", "DEV1"]}
    response = client.post(reverse("approval_bulk"), data)
    summary = client.get(response.url).content.decode()
    assert decision(org.dev1).status == "APPROVED"
    assert decision(org.dev2) is None
    assert "Approved 1: John Kim." in summary
    assert f"Skipped {org.dev2.first_name} {org.dev2.last_name}: Has flags" in summary
    assert "Skipped OPS1: You can&#x27;t approve this employee." in summary
    assert AuditLog.objects.filter(action="APPROVE").count() == 1


def test_pay_period_dates(org, login_as):
    """T-97: 14-day periods from the anchor; default = last completed; snapping; no future."""
    assert period_start_for(date(2026, 1, 4)) == date(2026, 1, 4)
    assert period_start_for(date(2026, 1, 17)) == date(2026, 1, 4)
    assert period_start_for(date(2026, 10, 1)) == PERIOD
    assert current_period(NOW) == CURRENT and default_period(NOW) == PERIOD
    assert recent_periods(NOW, 3) == [CURRENT, PERIOD, date(2026, 9, 13)]

    client = login_as(org.manager)
    page = client.get(reverse("approvals")).content.decode()
    assert 'id="period-label">Sep 27 – Oct 10, 2026<' in page
    assert 'href="?period=2026-09-13"' in page and 'href="?period=2026-10-11"' in page
    snapped = client.get(reverse("approvals"), {"period": "2026-10-01"}).content.decode()
    assert 'id="period-label">Sep 27 – Oct 10, 2026<' in snapped
    current = client.get(reverse("approvals"), {"period": "2026-10-20"}).content.decode()
    assert (
        'id="period-label">Oct 11 – Oct 24, 2026<' in current and 'id="next-period"' not in current
    )
    assert client.get(reverse("approvals"), {"period": "2026-10-25"}).status_code == 404
    assert client.get(reverse("approvals"), {"period": "soon"}).status_code == 404
    off_start = reverse("approval_detail", args=[date(2026, 10, 1), "DEV1"])
    assert client.get(off_start).url == detail_url(org.dev1)


def test_flags(org, make_week, login_as, project):
    """T-98: late, overtime (Break never counts) and missing days (leave counts) per D-55."""
    make_week(org.dev1, WEEK1, end=time(18))  # 9 h days = 45 h > 40 h → overtime
    make_week(org.dev1, WEEK2, is_late=True)  # late
    week1 = make_week(org.dev2, WEEK1, days=4)  # Friday empty → 1 missing day
    week2 = make_week(org.dev2, WEEK2)
    TimeEntryFactory(  # a long break on Monday: never counts as hours worked
        timesheet=week2,
        work_date=WEEK2 + timedelta(days=1),
        category="BREAK",
        project=None,
        start_time=time(17),
        end_time=time(19),
        minutes=120,
        reason="Lunch break",
    )
    TimeEntryFactory(  # an hour of PTO on Thursday: leave, not hours worked
        timesheet=week1,
        work_date=WEEK1 + timedelta(days=4),  # Thursday
        category="PTO",
        project=None,
        start_time=None,
        end_time=None,
        minutes=60,
        reason="Doctor",
    )
    rows = {r.employee.employee_code: r for r in period_rows(org.manager, PERIOD, NOW)}
    assert rows["DEV1"].flags == {"late": True, "overtime": True, "missing_days": 0}
    assert rows["DEV2"].flags == {"late": False, "overtime": False, "missing_days": 1}
    assert rows["DEV2"].worked == 9 * 480 and rows["DEV2"].leave == 60
    html = login_as(org.manager).get(reverse("approvals")).content.decode()
    assert "Missing 1 day<" in html and ">Overtime<" in html and ">Late<" in html


def test_leave_day_is_not_missing(org, make_week):
    """Helper check: a day with only leave is not a missing day (D-55)."""
    week1 = make_week(org.dev1, WEEK1, days=4)
    make_week(org.dev1, WEEK2)
    TimeEntryFactory(
        timesheet=week1,
        work_date=WEEK1 + timedelta(days=5),  # Friday
        category="PTO",
        project=None,
        start_time=None,
        end_time=None,
        minutes=480,
        reason="Vacation",
    )
    (row,) = [r for r in period_rows(org.manager, PERIOD, NOW) if r.employee == org.dev1]
    assert row.flags["missing_days"] == 0 and row.can_bulk


def test_forbidden_cases(org, make_week, login_as):
    """T-99: 403 for non-managers, non-direct reports, and admins on staff with a manager."""
    make_week(org.ops1, WEEK1)
    make_week(org.ops1, WEEK2)
    dev = login_as(org.dev1)
    assert dev.post(reverse("approval_bulk"), {"period": PERIOD.isoformat()}).status_code == 403
    assert dev.get(detail_url(org.ops1)).status_code == 403
    manager = login_as(org.manager)
    assert manager.get(detail_url(org.ops1)).status_code == 403
    assert post(manager, org.ops1, "approve").status_code == 403
    assert post(manager, org.ops1, "unlock", week=WEEK2.isoformat()).status_code == 403
    assert login_as(org.hr).get(detail_url(org.dev1)).status_code == 403  # dev1 has a manager
    assert manager.get(detail_url(org.manager)).status_code == 403  # self
    assert decision(org.ops1) is None


def test_period_partly_outside_employment(org, make_week, login_as):
    """T-100: only weeks with employment are required (hired in week 2, or left in week 1)."""
    joiner = EmployeeFactory(manager=org.manager, hire_date=WEEK2, employee_code="NEW1")
    leaver = EmployeeFactory(
        manager=org.manager,
        hire_date=date(2024, 1, 8),
        end_date=date(2026, 10, 1),
        status="INACTIVE",
        employee_code="LEFT1",
    )
    make_week(joiner, WEEK2)
    make_week(leaver, WEEK1, days=4)  # employed Mon–Thu (end Thursday Oct 1)
    client = login_as(org.manager)
    html = client.get(reverse("approvals")).content.decode()
    assert 'data-employee="NEW1"' in html and 'data-employee="LEFT1"' in html
    assert "Not employed this week" in client.get(detail_url(joiner)).content.decode()
    for person in (joiner, leaver):
        assert post(client, person, "approve").status_code == 302
        assert decision(person).status == "APPROVED"
    assert status(joiner, WEEK2) == status(leaver, WEEK1) == "APPROVED"
    assert not Timesheet.objects.filter(employee=joiner, week_start=WEEK1).exists()


def test_open_change_request_blocks_approval(org, make_week, login_as):
    """T-101: an open change request blocks approve/reject and bulk approve (D-58)."""
    sheet = make_week(org.dev1, WEEK1)
    make_week(org.dev1, WEEK2)
    ChangeRequest.objects.create(timesheet=sheet, requester=org.dev1, reason="Wrong project")
    client = login_as(org.manager)
    page = client.get(detail_url(org.dev1)).content.decode()
    assert "Handle the open change request on week 1 first." in page
    assert 'name="employee" value="DEV1"' not in client.get(reverse("approvals")).content.decode()
    post(client, org.dev1, "approve")
    post(client, org.dev1, "reject", comment="No")
    assert decision(org.dev1) is None


def test_week_page_shows_approval_status(org, make_week, login_as):
    """T-102: the employee's week page shows approved-by, the rejection comment, or waiting."""
    make_week(org.dev1, WEEK1)
    make_week(org.dev1, WEEK2)
    make_week(org.dev2, WEEK1)
    make_week(org.dev2, WEEK2)
    manager = login_as(org.manager)
    post(manager, org.dev1, "approve")
    post(manager, org.dev2, "reject", comment="Split the Monday hours.")
    manager_name = f"{org.manager.first_name} {org.manager.last_name}"

    dev1 = login_as(org.dev1).get(reverse("timesheet_week", args=[WEEK1])).content.decode()
    assert f"Approved by {manager_name} on Oct 21, 2026." in dev1
    dev2 = login_as(org.dev2).get(reverse("timesheet_week", args=[WEEK2])).content.decode()
    assert f"Rejected by {manager_name}" in dev2 and "Split the Monday hours." in dev2
    make_week(org.dev1, CURRENT)
    waiting = login_as(org.dev1).get(reverse("timesheet_week", args=[CURRENT])).content.decode()
    assert f"Waiting for approval by {manager_name}." in waiting


@pytest.mark.django_db
def test_inactive_employee_listed_only_with_timesheets(org, make_week, login_as):
    """Helper check: an inactive report without timesheets in the period is not listed (D-54)."""
    EmployeeFactory(manager=org.manager, status="INACTIVE", employee_code="GONE1")  # no end_date
    left = EmployeeFactory(manager=org.manager, status="INACTIVE", employee_code="GONE2")
    make_week(left, WEEK1)
    html = login_as(org.manager).get(reverse("approvals")).content.decode()
    assert 'data-employee="GONE1"' not in html and 'data-employee="GONE2"' in html
