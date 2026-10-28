"""Change 9: managers edit, approve or reject every required person — submitted or locked
(D-139–D-141); the register waits for everyone (D-142); payroll and HR see who is pending
(D-143)."""

import csv
import io
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.urls import reverse

from analytics.services.metrics import dashboard_for
from audit.models import AuditLog
from payroll.models import PayrollRegister, PayrollRegisterLine, PayrollWeek
from payroll.services.register import OPEN, READY, finalize, period_state
from tests.factories import EmployeeFactory
from tests.forms import form, work
from timesheets.models import PeriodApproval, Timesheet
from timesheets.services.approvals import approve_period, period_row
from timesheets.services.calendar import effective_status, week_state
from timesheets.services.changes import raise_request

pytestmark = pytest.mark.django_db(databases=["default", "payroll"])

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)  # fixed_now
PERIOD = date(2026, 9, 27)  # weeks of Sep 27 + Oct 4: both past their deadline
WEEK1, WEEK2 = PERIOD, PERIOD + timedelta(weeks=1)
MON, TUE, WED = (WEEK1 + timedelta(days=n) for n in (1, 2, 3))
CURRENT = date(2026, 10, 11)


def detail_url(person, period=PERIOD):
    return reverse("approval_detail", args=[period, person.employee_code])


def edit_url(person, week, period=PERIOD):
    return reverse("approval_week_edit", args=[period, person.employee_code, week])


def approve(client, person, confirm=True, period=PERIOD):
    data = {"action": "approve", **({"confirm_unsubmitted": "1"} if confirm else {})}
    return client.post(detail_url(person, period), data)


def messages_after(client, response):
    return client.get(response.url).content.decode()


def test_manager_edits_a_locked_week(org, project, make_week, login_as, fixed_now):
    """T-217: the approver edits a LOCKED week — a draft the employee never submitted, or no
    timesheet at all — in the weekly grid; saved and audited; it stays locked and unsubmitted;
    invalid entries are refused; a submitted week stays submitted (D-140, D-141)."""
    draft = make_week(org.dev1, WEEK1, "DRAFT", days=2)  # Mon–Tue entered, never submitted
    client = login_as(org.manager)
    page = client.get(detail_url(org.dev1)).content.decode()
    assert "Edit week 1" in page and "Edit week 2" in page
    assert page.count(">Not submitted by employee<") == 2
    html = client.get(edit_url(org.dev1, WEEK1)).content.decode()
    assert len(re.findall(r'class="grid-slot" data-index="\d+"', html)) == 2  # the draft
    rows = form(
        work(MON, "09:00", "17:00", project),
        work(TUE, "09:00", "17:00", project),
        work(WED, "09:00", "12:00", project, reason=""),
    )
    response = client.post(edit_url(org.dev1, WEEK1), rows)
    assert response.url == detail_url(org.dev1)
    draft.refresh_from_db()
    assert draft.entries.count() == 3 and draft.submitted_at is None
    assert effective_status(draft, NOW) == "LOCKED"  # still locked, not submitted
    audit = AuditLog.objects.get(action="UPDATE", entity_id=str(draft.pk))
    assert audit.actor == org.manager and audit.after["via"] == "approvals"
    assert (len(audit.before["entries"]), len(audit.after["entries"])) == (2, 3)
    assert audit.before["status"] == audit.after["status"] == "LOCKED"

    client.post(
        edit_url(org.dev1, WEEK2), form(work(WEEK2 + timedelta(days=1), "09:00", "13:00", project))
    )
    created = Timesheet.objects.get(employee=org.dev1, week_start=WEEK2)  # no timesheet before
    assert (created.status, created.submitted_at, created.entries.count()) == ("LOCKED", None, 1)
    assert week_state(org.dev1, WEEK2, created, NOW).is_missed  # still a missed week (D-75)

    clash = form(work(MON, "09:00", "12:00", project), work(MON, "11:00", "13:00", project))
    html = client.post(edit_url(org.dev1, WEEK1), clash).content.decode()
    assert "overlap" in html and draft.entries.count() == 3  # nothing saved

    submitted = make_week(org.dev2, WEEK1)
    client.post(edit_url(org.dev2, WEEK1), form(work(MON, "09:00", "18:00", project)))
    submitted.refresh_from_db()
    assert submitted.status == "SUBMITTED" and submitted.submitted_at is not None
    assert submitted.entries.get().minutes == 540


def test_approve_with_a_locked_week(
    org, project, make_week, login_as, fixed_now, django_capture_on_commit_callbacks
):
    """T-218: approving with a LOCKED week needs the confirmation; then both weeks APPROVED
    with the hours entered, published to payroll (0.00 too), audited, marked "not submitted
    by employee" — and the dashboard still counts the week as missed (D-139, D-141, D-75)."""
    make_week(org.dev1, WEEK1)
    make_week(org.dev1, WEEK2, "DRAFT", days=3)  # 24 h entered, never submitted
    client = login_as(org.manager)
    page = client.get(detail_url(org.dev1)).content.decode()
    assert "Week 2 was not submitted by John Kim; it will be approved with 24.00 hours." in page
    assert "Week 2 has 2 missing days." in page  # Thu and Fri empty
    refused = approve(client, org.dev1, confirm=False)
    assert "Confirm to approve" in messages_after(client, refused)
    assert not PeriodApproval.objects.filter(status="APPROVED").exists()
    with django_capture_on_commit_callbacks(execute=True):
        approve(client, org.dev1)
    approval = PeriodApproval.objects.get(employee=org.dev1)
    assert approval.status == "APPROVED" and approval.approver == org.manager
    week2 = Timesheet.objects.get(employee=org.dev1, week_start=WEEK2)
    assert week2.status == "APPROVED" and week2.submitted_at is None  # the marker (D-141)
    audit = AuditLog.objects.get(action="APPROVE")
    assert audit.after["not_submitted_by_employee"] == ["2026-10-04"]
    record = PayrollWeek.objects.get(employee_code="DEV1", week_start=WEEK2)
    assert record.total_minutes == 1440

    page = client.get(reverse("approvals"), {"period": PERIOD.isoformat()}).content.decode()
    row = page.split('data-employee="DEV1"')[1].split("</tr>")[0]
    assert ">Not submitted by employee<" in row
    employee_page = login_as(org.dev1).get(reverse("timesheet_week", args=[WEEK2]))
    assert 'id="approved-unsubmitted"' in employee_page.content.decode()
    assert week_state(org.dev1, WEEK2, week2, NOW).is_missed  # still missed after approval
    dashboard = dashboard_for(org.dev1, 4, NOW)  # Sep 27 on time; Oct 4 and Oct 11 missed
    assert (dashboard.punctuality.on_time, dashboard.punctuality.missed) == (1, 2)

    with django_capture_on_commit_callbacks(execute=True):  # nothing entered at all: 0.00
        approve(login_as(org.manager), org.dev2)
    assert {r.total_minutes for r in PayrollWeek.objects.filter(employee_code="DEV2")} == {0}
    assert Timesheet.objects.filter(employee=org.dev2, status="APPROVED").count() == 2


def test_reject_a_locked_person(org, project, make_week, login_as, fixed_now):
    """T-219: rejecting a LOCKED person reopens their weeks (created if needed); while the
    window is open the manager waits; a resubmission makes it pending again; a window that
    ends unsubmitted makes the weeks LOCKED and decidable again (D-139, D-21, D-60)."""
    client = login_as(org.manager)
    response = client.post(detail_url(org.dev1), {"action": "reject", "comment": "Fill it in"})
    assert response.status_code == 302
    sheets = Timesheet.objects.filter(employee=org.dev1).order_by("week_start")
    assert [s.status for s in sheets] == ["REOPENED", "REOPENED"]
    assert sheets[0].reopen_until == NOW + timedelta(hours=48)
    page = client.get(detail_url(org.dev1)).content.decode()
    assert "Week 1 is reopened until Fri Oct 23, 10:00 AM — waiting for John to resubmit." in page
    assert "Edit week 1" not in page and 'value="approve"' not in page
    assert "waiting for John" in messages_after(client, client.get(edit_url(org.dev1, WEEK1)))
    assert "waiting for John" in messages_after(client, approve(client, org.dev1))

    employee = login_as(org.dev1)
    for week in (WEEK1, WEEK2):
        day = week + timedelta(days=1)
        employee.post(
            reverse("timesheet_week", args=[week]),
            form(work(day, "09:00", "17:00", project), action="submit"),
        )
    assert PeriodApproval.objects.get(employee=org.dev1).status == "PENDING"  # D-60
    assert period_row(org.manager, org.dev1, PERIOD, NOW).blockers == []

    login_as(org.manager).post(detail_url(org.dev2), {"action": "reject", "comment": "Again"})
    later = NOW + timedelta(hours=49)  # the window ended without a resubmission
    row = period_row(org.manager, org.dev2, PERIOD, later)
    assert [w.state.status for w in row.weeks] == ["LOCKED", "LOCKED"] and row.blockers == []


def test_refusals(org, project, make_week, login_as, fixed_now):
    """T-220: refused — not the approver or one's own period (403), an open change request, a
    week outside employment, an approved period, a draft in a running week; bulk approve skips
    locked rows (D-139, D-140, D-63)."""
    for person, target in ((org.ops_manager, org.dev1), (org.manager, org.manager)):
        client = login_as(person)
        assert client.get(edit_url(target, WEEK1)).status_code == 403
        assert approve(client, target).status_code == 403
        rows_url = reverse("approval_week_rows", args=[PERIOD, target.employee_code, WEEK1])
        assert (
            client.post(rows_url, {"row-action": "delete", "row-key": "MEETING:"}).status_code
            == 403
        )

    make_week(org.dev1, WEEK1)
    make_week(org.dev1, WEEK2)
    raise_request(org.dev1, WEEK1, "Monday is wrong", now=NOW)
    client = login_as(org.manager)
    assert "Handle the open change request" in messages_after(
        client, client.get(edit_url(org.dev1, WEEK1))
    )
    assert "Handle the open change request" in messages_after(client, approve(client, org.dev1))

    late_hire = EmployeeFactory(employee_code="NEW1", manager=org.manager, hire_date=WEEK2)
    page = client.get(detail_url(late_hire)).content.decode()
    assert "Edit week 1" not in page and "Edit week 2" in page
    assert "wasn&#x27;t employed this week" in messages_after(
        client, client.get(edit_url(late_hire, WEEK1))
    )

    make_week(org.dev2, WEEK1)
    make_week(org.dev2, WEEK2)
    approve(client, org.dev2)
    assert "already approved" in messages_after(client, client.get(edit_url(org.dev2, WEEK1)))

    make_week(org.ops1, CURRENT + timedelta(weeks=1), "DRAFT")  # the running week
    ops = login_as(org.ops_manager)
    response = ops.get(edit_url(org.ops1, CURRENT + timedelta(weeks=1), CURRENT))
    assert "hasn&#x27;t been submitted yet" in messages_after(ops, response)

    make_week(org.ops1, WEEK1)  # clean, submitted
    make_week(org.ops1, WEEK2)
    for person in (org.ops1,):  # bulk: OPS1 clean; the director's MANAGER row is locked
        assert period_row(org.ops_manager, person, PERIOD, NOW).can_bulk
    director = login_as(org.director)
    response = director.post(
        reverse("approval_bulk"), {"period": PERIOD.isoformat(), "employee": ["MANAGER"]}
    )
    assert "Skipped Priya Shah" in messages_after(director, response)
    assert not PeriodApproval.objects.filter(employee=org.manager, status="APPROVED").exists()


def test_hr_decides_the_ceo(org, project, login_as, fixed_now, django_capture_on_commit_callbacks):
    """T-221: HR (an admin) edits and approves the CEO, who has no manager, the same way; the
    CEO can't approve themselves and a manager can't approve the CEO (D-11, D-139)."""
    hr = login_as(org.hr)
    assert hr.get(edit_url(org.ceo, WEEK1)).status_code == 200
    hr.post(edit_url(org.ceo, WEEK1), form(work(MON, "09:00", "17:00", project)))
    assert Timesheet.objects.get(employee=org.ceo, week_start=WEEK1).entries.count() == 1
    with django_capture_on_commit_callbacks(execute=True):
        approve(hr, org.ceo)
    approval = PeriodApproval.objects.get(employee=org.ceo)
    assert approval.status == "APPROVED" and approval.approver == org.hr
    assert PayrollWeek.objects.get(employee_code="CEO", week_start=WEEK1).total_minutes == 480
    assert approve(login_as(org.ceo), org.ceo).status_code == 403
    assert login_as(org.director).get(edit_url(org.ceo, WEEK1)).status_code == 403


def test_register_waits_for_everyone(
    org, approve_everyone, login_as, fixed_now, django_capture_on_commit_callbacks
):
    """T-222: after the deadline the register stays OPEN while anyone is unapproved — the page
    shows progress and who is pending, no hours or downloads; Finalize is refused; READY after
    the last approval, with no 0.00 "not submitted" lines; a register saved under Change 8
    keeps its 0.00 line (D-142)."""
    old = PayrollRegister.objects.create(
        period_start=date(2026, 8, 30), period_end=date(2026, 9, 12), export_batch="EXP-0001",
        ready_reason="DEADLINE", required_count=1, approved_count=0, finalized_at=NOW,
        finalized_by_name="test",
    )  # fmt: skip
    PayrollRegisterLine.objects.create(
        register=old, employee_code="DEV2", employee_name="Sara Ng", department="Technology",
        status="NOT_SUBMITTED",
    )  # fmt: skip
    for person in [e for e in vars(org).values() if e != org.dev2]:  # all but DEV2
        with django_capture_on_commit_callbacks(execute=True):
            approve_period(
                person.manager or org.hr, person, PERIOD, now=NOW, confirm_unsubmitted=True
            )
    state = period_state(PERIOD, NOW)
    assert (state.status, state.approved, state.required) == (OPEN, 9, 10)
    assert state.deadline_passed  # Overdue, still OPEN
    client = login_as(org.payroll)
    page = client.get(reverse("payroll_period", args=[PERIOD])).content.decode()
    assert 'id="register"' not in page and "Download register CSV" not in page
    assert 'id="payroll-records"' not in page  # no hours at all while OPEN
    assert "Sara Ng" in page.split('id="pending-by-manager"')[1] and ">Overdue<" in page
    with pytest.raises(Exception, match="not approved"):
        finalize(PERIOD, system_actor="test", now=NOW)

    approve_everyone(PERIOD, NOW)  # the last one: DEV2, locked with nothing entered
    assert period_state(PERIOD, NOW).status == READY
    register = finalize(PERIOD, system_actor="test", now=NOW)
    assert set(register.lines.values_list("status", flat=True)) == {"APPROVED"}
    assert register.lines.get(employee_code="DEV2").pay_total_minutes == 0
    old_page = client.get(reverse("payroll_period", args=[old.period_start])).content.decode()
    assert "Missed – not submitted" in old_page  # saved registers never change


def test_pending_by_manager(org, project, make_week, login_as, fixed_now, approve_everyone):
    """T-223: payroll and HR see, per manager, who is still to approve and why (submitted,
    locked – not submitted, reopened until …, change request), Overdue after the deadline,
    the totals and a CSV; everyone else gets 403 (D-143)."""
    make_week(org.dev1, WEEK1)  # submitted, waiting for Priya
    make_week(org.dev1, WEEK2)
    make_week(org.payroll, WEEK1)
    make_week(org.payroll, WEEK2)
    raise_request(org.payroll, WEEK1, "Wrong project", now=NOW)
    login_as(org.ops_manager).post(detail_url(org.ops1), {"action": "reject", "comment": "Fix"})
    approved = [org.hr, org.director, org.manager, org.ops_manager, org.finance]
    for person in approved:
        PeriodApproval.objects.create(employee=person, period_start=PERIOD, status="APPROVED")
    client = login_as(org.payroll)
    html = client.get(reverse("payroll_pending")).content.decode()  # default: Sep 27 – Oct 10
    assert "Pay period Sep 27 – Oct 10, 2026" in html
    assert "Managers done <strong>2 of 6</strong>" in html  # Asha Rao and Mark Lee are done
    assert "people approved <strong>5 of 10</strong>" in html

    def group(code):
        return html.split(f'data-manager="{code}"')[1].split("</tr>")[0]

    priya = group("MANAGER")
    assert "Priya Shah" in priya and "2 of 2" in priya
    assert "John Kim" in priya and "— Submitted" in priya
    assert "Sara Ng" in priya and "— Locked – not submitted" in priya
    assert "Reopened until Fri Oct 23, 10:00 AM" in group("OPSMGR")
    assert "Change request open" in group("FINANCE")
    assert "Asha Rao" in group("ADMINS") and "HR / admins" in group("ADMINS")
    assert group("MANAGER").count(">Overdue<") == 2

    response = client.get(reverse("payroll_pending_csv"), {"period": PERIOD.isoformat()})
    assert (
        'filename="payroll-pending_2026-09-27_to_2026-10-10.csv"'
        in (response["Content-Disposition"])
    )
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert {(r["approver"], r["employee_code"], r["state"]) for r in rows} >= {
        ("Priya Shah", "DEV1", "Submitted"),
        ("Priya Shah", "DEV2", "Locked – not submitted"),
        ("HR / admins", "CEO", "Locked – not submitted"),
    }
    assert {r["overdue"] for r in rows} == {"yes"}

    payroll_list = client.get(reverse("payroll")).content.decode()
    assert f"{reverse('payroll_pending')}?period=2026-09-27" in payroll_list  # "Who's pending"
    assert reverse("payroll_pending") in login_as(org.hr).get("/admin/").content.decode()
    assert login_as(org.hr).get(reverse("payroll_pending")).status_code == 200
    for person in (org.dev1, org.manager, org.director):
        other = login_as(person)
        assert other.get(reverse("payroll_pending")).status_code == 403
        assert other.get(reverse("payroll_pending_csv")).status_code == 403
    with time_machine.travel(datetime(2026, 10, 12, 9, 0, tzinfo=TZ), tick=False):
        early = login_as(org.payroll).get(reverse("payroll_pending")).content.decode()
    assert ">Overdue<" not in early  # before Monday 12:00 nothing is overdue


def test_edit_page_helpers(org, project, make_week, login_as, fixed_now):
    """Helper check: the edit page's live day summary and row menu work for the approver only,
    unreadable input is shown again, a week outside the period is 404, a running week shows as
    "Not submitted yet" for payroll (D-140, D-143)."""
    client = login_as(org.manager)
    args = [PERIOD, "DEV1", WEEK1]
    posted = form(work(MON, "09:00", "12:00", project))
    summary = client.post(reverse("approval_week_totals", args=args), posted)
    assert summary.status_code == 200 and 'id="day-summary"' in summary.content.decode()
    rows = client.post(
        reverse("approval_week_rows", args=args),
        {**posted, "row-action": "delete", "row-key": f"PROJECT:{project.pk}:DEV"},
    )
    assert rows.status_code == 200 and rows.context["grid"].rows == []
    bad = client.post(edit_url(org.dev1, WEEK1), form(work(MON, "9am", "12:00", project)))
    assert "times must look like 08:30" in bad.content.decode()
    assert not Timesheet.objects.filter(employee=org.dev1).exists()  # nothing saved
    wrong_week = reverse("approval_week_edit", args=[PERIOD, "DEV1", CURRENT])
    assert client.get(wrong_week).status_code == 404

    make_week(org.dev2, WEEK1)
    make_week(org.dev2, WEEK2)
    client.post(detail_url(org.dev2), {"action": "approve"})  # approved: no more edits here
    dev2_args = [PERIOD, "DEV2", WEEK1]
    assert client.post(reverse("approval_week_rows", args=dev2_args), posted).status_code == 403
    assert client.post(reverse("approval_week_totals", args=dev2_args), posted).status_code == 403

    make_week(org.ops1, CURRENT)  # week 1 submitted …
    make_week(org.ops1, CURRENT + timedelta(weeks=1), "DRAFT")  # … the running week a draft
    page = login_as(org.payroll).get(reverse("payroll_pending"), {"period": CURRENT.isoformat()})
    lena = page.content.decode().split('data-employee="OPS1">')[1].split("</li>")[0]
    assert "— Not submitted yet" in lena
