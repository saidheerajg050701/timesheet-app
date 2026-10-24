import re
from datetime import datetime, time, timedelta
from pathlib import Path

from django.urls import reverse
from playwright.sync_api import expect

from audit.models import AuditLog
from tests.e2e.conftest import E2E, PERIOD, THIS_WEEK, TZ, log_in
from tests.factories import TEST_PASSWORD
from timesheets.models import ChangeRequest, PeriodApproval
from timesheets.services.approvals import approve_period

pytestmark = E2E
NEW_PASSWORD = "Brand-New-Pass-2026"
WEEK2 = PERIOD + timedelta(weeks=1)


def week_url(week):
    return reverse("timesheet_week", args=[week])


def status_of(page):
    return page.locator("#week-status")


def test_signup_refused_then_accepted(e2e_org, anonymous):
    """T-146: E2E sign-up refused for an unknown email, accepted for a directory employee."""
    page = anonymous
    page.goto("/signup/")
    page.get_by_label("Email").fill("nobody@yourcompany.com")
    page.get_by_label("Password", exact=True).fill(NEW_PASSWORD)
    page.get_by_label("Confirm password").fill(NEW_PASSWORD)
    page.get_by_role("button", name="Sign up").click()
    expect(page.get_by_text("not in the company employee directory")).to_be_visible()

    page.goto("/signup/")
    page.get_by_label("Email").fill("QA1@yourcompany.com")
    page.get_by_label("Password", exact=True).fill(NEW_PASSWORD)
    page.get_by_label("Confirm password").fill(NEW_PASSWORD)
    page.get_by_role("button", name="Sign up").click()
    expect(page.get_by_text("Welcome, Ravi! Your account is ready.")).to_be_visible()
    expect(page.locator("nav.navbar")).to_contain_text("Ravi Kumar")
    expect(page.locator("nav.navbar")).to_contain_text("QA1")


def test_save_draft_then_submit_before_the_deadline(e2e_org, open_as):
    """T-147: E2E save a draft, reopen it, then submit before Saturday 12:00."""
    page = open_as(e2e_org.dev1)
    page.goto(week_url(THIS_WEEK))
    expect(status_of(page)).to_have_text("Not started")
    page.get_by_label("Day, row 1").select_option(THIS_WEEK.isoformat())
    page.get_by_label("Category, row 1").select_option("PROJECT")
    page.get_by_label("Project, row 1").select_option(label="PRJ-001 Customer Portal")
    page.get_by_label("Start time, row 1").fill("09:00")
    page.get_by_label("End time, row 1").fill("17:00")
    page.get_by_label("Reason, row 1").fill("Login page")
    page.get_by_role("button", name="Save draft").click()
    expect(status_of(page)).to_have_text("Draft")

    page.goto(week_url(THIS_WEEK))  # reopened: the row is still there
    expect(page.get_by_label("Reason, row 1")).to_have_value("Login page")
    expect(page.get_by_label("Hours, row 1")).to_have_value("8.00")
    page.get_by_role("button", name="Submit").click()
    expect(status_of(page)).to_have_text("Submitted")
    expect(page.get_by_role("button", name="Save draft")).to_have_count(0)
    expect(page.locator("#entry-rows input")).to_have_count(0)  # read-only now
    expect(page.locator("#entry-rows")).to_contain_text("Login page")


def test_week_locks_after_the_deadline(e2e_org, make_week, open_as, clock):
    """T-148: E2E an unsubmitted week is locked from Saturday 12:00 (fixed clock)."""
    make_week(e2e_org.dev1, THIS_WEEK, status="DRAFT")
    page = open_as(e2e_org.dev1)
    page.goto(week_url(THIS_WEEK))
    expect(page.get_by_role("button", name="Submit")).to_be_visible()

    clock.move_to(datetime(2026, 10, 24, 12, 0, tzinfo=TZ))  # Saturday 12:00
    page.goto(week_url(THIS_WEEK))
    expect(status_of(page)).to_have_text("Locked")
    expect(page.get_by_role("button", name="Submit")).to_have_count(0)
    expect(page.get_by_role("button", name="Save draft")).to_have_count(0)
    expect(page.locator("#entry-rows input")).to_have_count(0)
    expect(page.locator("#entry-rows")).to_contain_text("Feature work")


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
    manager.get_by_label("End time, row 1").fill("18:00")
    manager.get_by_label("Note to the employee (optional)").fill("Fixed Monday")
    manager.get_by_role("button", name="Save and submit for the employee").click()
    expect(manager.get_by_role("alert")).to_have_text(
        "Week edited and submitted on the employee's behalf."
    )

    employee.goto(week_url(week))
    expect(status_of(employee)).to_have_text("Submitted")
    expect(employee.locator("#row-0")).to_contain_text("18:00")
    change = ChangeRequest.objects.get(timesheet__employee=e2e_org.dev1)
    row = AuditLog.objects.get(action="UPDATE", change_request=change)
    assert row.actor == e2e_org.manager
    assert "18:00" in str(row.after) and "17:00" in str(row.before)


def test_approve_then_payroll_sees_the_records(e2e_org, make_week, open_as):
    """T-150: E2E manager approves a period; the payroll user sees both week records."""
    make_week(e2e_org.dev1, PERIOD, monday_end=time(19))  # 42 h: 2 h overtime
    make_week(e2e_org.dev1, WEEK2)
    manager = open_as(e2e_org.manager)
    manager.goto(reverse("approval_detail", args=[PERIOD, "DEV1"]))
    manager.get_by_role("button", name="Approve both weeks").click()
    expect(manager.get_by_role("alert")).to_have_text("Approved John's period.")

    payroll = open_as(e2e_org.payroll)
    payroll.goto(f"{reverse('payroll')}?period={PERIOD.isoformat()}")
    records = payroll.locator("#payroll-records tbody tr", has_text="John Kim")
    expect(records).to_have_count(2)
    expect(records.filter(has_text="Sep 28")).to_contain_text("40.00")
    expect(records.filter(has_text="Sep 28")).to_contain_text("2.00")  # overtime
    expect(records.filter(has_text="Oct 5")).to_contain_text("Current")


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
            employee.get_by_label("Reason, row 5").fill("Feature work and demo")
        employee.get_by_role("button", name="Submit").click()
        expect(status_of(employee)).to_have_text("Submitted")

    manager.goto(detail)
    expect(manager.get_by_role("button", name="Approve both weeks")).to_be_enabled()


def test_payroll_export_and_mark_paid(e2e_org, make_week, open_as, clock):
    """T-152: E2E payroll exports the period as CSV, then marks the batch paid."""
    make_week(e2e_org.dev1, PERIOD)
    make_week(e2e_org.dev1, WEEK2)
    approve_period(e2e_org.manager, e2e_org.dev1, PERIOD, now=datetime.now(TZ))  # publishes
    page = open_as(e2e_org.payroll)
    page.goto(f"{reverse('payroll')}?period={PERIOD.isoformat()}")
    with page.expect_download() as download:
        page.get_by_role("button", name=re.compile(r"Export CSV \(2 new week records\)")).click()
    text = Path(download.value.path()).read_text(encoding="utf-8-sig")
    assert text.startswith("batch,employee_code") and text.count("DEV1") == 2

    page.goto(f"{reverse('payroll')}?period={PERIOD.isoformat()}")
    expect(page.locator("#payroll-records")).to_contain_text("Exported")
    page.get_by_role("button", name="Mark as paid").click()
    expect(page.locator("#batches")).to_contain_text("Paid")
    expect(page.locator("#payroll-records tbody tr", has_text="Paid")).to_have_count(2)


def test_hr_deactivates_an_employee(e2e_org, open_as, anonymous):
    """T-153: E2E HR deactivates an employee, who is logged out and cannot log in again."""
    employee = open_as(e2e_org.dev2)
    hr = open_as(e2e_org.hr)
    hr.goto("/admin/directory/employee/")
    hr.locator("tr", has_text="DEV2").get_by_role("checkbox").check()
    hr.locator('select[name="action"]').select_option("deactivate")
    hr.get_by_role("button", name="Go").click()
    expect(hr.get_by_label("End date (last working day)")).to_have_value("2026-10-21")
    hr.get_by_role("button", name="Deactivate").click()
    expect(hr.get_by_text("Deactivated 1 employee(s).")).to_be_visible()

    employee.goto("/")
    expect(employee).to_have_url(re.compile(r"/login/"))
    log_in(anonymous, e2e_org.dev2.email, TEST_PASSWORD)
    expect(anonymous.get_by_text("Wrong email or password.")).to_be_visible()


def test_hr_password_reset_forces_a_change(e2e_org, open_as, anonymous):
    """T-154: E2E HR sets a temporary password; the employee must change it at next login."""
    temporary = "Temporary-Pass-2026"
    hr = open_as(e2e_org.hr)
    hr.goto(f"/admin/directory/employee/{e2e_org.dev1.pk}/change/")
    hr.get_by_role("link", name="Reset password").click()
    hr.get_by_label("Temporary password:", exact=True).fill(temporary)
    hr.get_by_label("Temporary password (again):").fill(temporary)
    hr.get_by_role("button", name="Set temporary password").click()
    expect(hr.get_by_text("They must choose a new one at their next login")).to_be_visible()

    page = anonymous
    log_in(page, e2e_org.dev1.email, temporary)
    expect(page).to_have_url(re.compile(r"/profile/$"))
    expect(page.get_by_text("Choose a new password before you continue.")).to_be_visible()
    page.goto(reverse("timesheets"))
    expect(page).to_have_url(re.compile(r"/profile/$"))
    page.get_by_label("Current password").fill(temporary)
    page.get_by_label("New password", exact=True).fill(NEW_PASSWORD)
    page.get_by_label("Confirm new password").fill(NEW_PASSWORD)
    page.get_by_role("button", name="Change password").click()
    expect(page.get_by_text("Your password was changed.")).to_be_visible()
    page.goto(reverse("timesheets"))
    expect(page).to_have_url(re.compile(r"/timesheets/$"))


def test_forbidden_pages(e2e_org, open_as):
    """T-155: E2E 403 pages for an employee, a payroll-only user and a manager outside a tree."""
    cases = {
        e2e_org.dev1: ["/team/", "/approvals/", "/payroll/", "/admin/"],
        e2e_org.payroll: ["/team/", "/approvals/"],
        e2e_org.manager: [reverse("team_member", args=["OPS1"])],
    }
    for person, urls in cases.items():
        page = open_as(person)
        for url in urls:
            response = page.goto(url)
            assert response.status == 403, (person, url)
            expect(page.get_by_role("heading", name="Not allowed")).to_be_visible()
    assert not PeriodApproval.objects.exists()
