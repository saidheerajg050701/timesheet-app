"""Browser tests: change requests, Edit directly, approvals and manager decisions."""

from datetime import datetime, timedelta

from django.urls import reverse
from playwright.sync_api import expect

from apps.audit.models import AuditLog
from apps.directory.models import Employee
from apps.timesheets.models import ChangeRequest, Timesheet
from apps.timesheets.services.approvals import approve_period
from tests.e2e.conftest import E2E, PERIOD, THIS_WEEK, TZ
from tests.e2e.helpers import (
    PORTAL,
    WEEK2,
    add_row,
    cell,
    open_cell,
    status_of,
    week_url,
)

pytestmark = E2E


def test_change_request_then_manager_edits_directly(e2e_org, make_week, open_as):
    """T-149: E2E change request → manager Edit directly → employee sees it; audit row kept."""
    week = THIS_WEEK - timedelta(weeks=1)
    make_week(e2e_org.dev1, week)
    employee = open_as(e2e_org.dev1)
    employee.goto(week_url(week))
    employee.get_by_text("Request change").click()
    employee.get_by_label("What needs to change, and why?").fill("Monday ran until 18:00")
    employee.get_by_role("button", name="Send to my manager").click()
    expect(employee.locator("#change-request")).to_contain_text("Waiting for your manager")

    manager = open_as(e2e_org.manager)
    manager.goto(reverse("request_inbox"))
    manager.locator("#open-requests").get_by_role("link").first.click()
    manager.get_by_role("link", name="Edit directly").click()
    panel = open_cell(manager, PORTAL, week + timedelta(days=1))  # Monday
    panel.get_by_label("End").first.fill("18:00")  # the saved slot; an empty one is offered too
    panel.get_by_role("button", name="Done").click()
    expect(cell(manager, PORTAL, week + timedelta(days=1))).to_have_text("9.00")
    manager.get_by_label("Note to the employee (optional)").fill("Fixed Monday")
    manager.get_by_role("button", name="Save and submit for the employee").click()
    expect(manager.get_by_role("alert")).to_have_text(
        "Week edited and submitted on the employee's behalf."
    )

    employee.goto(week_url(week))
    expect(status_of(employee)).to_have_text("Submitted")
    expect(open_cell(employee, PORTAL, week + timedelta(days=1))).to_contain_text("18:00")
    change = ChangeRequest.objects.get(timesheet__employee=e2e_org.dev1)
    row = AuditLog.objects.get(action="UPDATE", change_request=change)
    assert row.actor == e2e_org.manager
    assert "18:00" in str(row.after) and "17:00" in str(row.before)


def test_reject_with_comment_then_resubmit(e2e_org, make_week, open_as):
    """T-151: E2E reject with a comment; the employee sees it and resubmits both weeks."""
    make_week(e2e_org.dev1, PERIOD)
    make_week(e2e_org.dev1, WEEK2)
    manager = open_as(e2e_org.manager)
    detail = reverse("approval_detail", args=[PERIOD, "DEV1"])
    manager.goto(detail)
    manager.get_by_label("Comment for the employee (required to reject)").fill("Add Friday's demo")
    manager.get_by_role("button", name="Reject").click()
    expect(manager.get_by_role("alert")).to_have_text("Rejected — John can fix and resubmit.")

    employee = open_as(e2e_org.dev1)
    for week in (PERIOD, WEEK2):  # both weeks reopened, with the comment
        employee.goto(week_url(week))
        expect(status_of(employee)).to_have_text("Reopened")
        expect(employee.locator("#approval-status")).to_contain_text("Add Friday's demo")
    for week in (PERIOD, WEEK2):  # a resubmission sets the period back to pending
        employee.goto(week_url(week))
        if week == PERIOD:
            panel = open_cell(employee, PORTAL, PERIOD + timedelta(days=5))  # Friday
            panel.get_by_label("Reason").first.fill("Feature work and demo")
            panel.get_by_role("button", name="Done").click()
        employee.get_by_role("button", name="Submit").click()
        expect(status_of(employee)).to_have_text("Submitted")

    manager.goto(detail)
    expect(manager.get_by_role("button", name="Approve both weeks")).to_be_enabled()


def test_manager_edits_and_approves_a_locked_employee(e2e_org, open_as):
    """T-224: E2E Sara never submitted (both weeks locked): her manager enters her hours in the
    grid, approves through the confirmation — the last approval — and payroll's register turns
    READY and is finalized & exported (D-139–D-142)."""
    for person in Employee.objects.exclude(pk=e2e_org.dev2.pk):  # everyone else: approved
        approver = person.manager or e2e_org.hr
        approve_period(approver, person, PERIOD, now=datetime.now(TZ), confirm_unsubmitted=True)
    payroll = open_as(e2e_org.payroll)
    payroll.goto(reverse("payroll_period", args=[PERIOD]))
    expect(payroll.locator("#register-status")).to_have_text("Open")  # deadline passed: Overdue
    expect(payroll.locator("#pending-by-manager")).to_contain_text("Locked – not submitted")

    manager = open_as(e2e_org.manager)
    manager.goto(reverse("approval_detail", args=[PERIOD, "DEV2"]))
    expect(manager.locator("#week-1")).to_contain_text("Not submitted by employee")
    manager.get_by_role("link", name="Edit week 1").click()
    add_row(manager, "Project work", "I-001 Customer Portal")
    monday = PERIOD + timedelta(days=1)
    panel = open_cell(manager, PORTAL, monday)
    panel.get_by_label("Start").fill("09:00")
    panel.get_by_label("End").fill("17:00")
    panel.get_by_role("button", name="Done").click()
    manager.get_by_role("button", name="Save the week").click()
    expect(manager.get_by_role("alert")).to_contain_text("Week of Sep 27 saved for Sara.")

    manager.get_by_role("button", name="Approve both weeks").click()
    dialog = manager.locator("#approve-dialog")
    expect(dialog).to_contain_text(
        "Week 1 was not submitted by Sara Ng; it will be approved with 8.00 hours."
    )
    expect(dialog).to_contain_text("Week 2 has 0.00 hours.")
    dialog.get_by_role("button", name="Approve both weeks").click()
    expect(manager.get_by_role("alert")).to_have_text("Approved Sara's period.")
    sheet = Timesheet.objects.get(employee=e2e_org.dev2, week_start=PERIOD)
    assert (sheet.status, sheet.submitted_at) == ("APPROVED", None)

    payroll.reload()
    expect(payroll.locator("#register-status")).to_have_text("Ready")
    payroll.get_by_role("button", name="Finalize & export").click()
    payroll.locator("#finalize-dialog").get_by_role("button", name="Finalize & export").click()
    expect(payroll.get_by_role("alert")).to_contain_text("exported as batch EXP-0001")
    sara = payroll.locator('#register tr[data-employee="DEV2"]')
    expect(sara.locator('[data-role="pay-total"]')).to_have_text("8.00")
