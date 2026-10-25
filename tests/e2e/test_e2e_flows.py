import re
from datetime import datetime, time, timedelta
from pathlib import Path

from django.urls import reverse
from playwright.sync_api import expect

from audit.models import AuditLog
from tests.e2e.conftest import E2E, PERIOD, THIS_WEEK, TZ, log_in
from tests.factories import TEST_PASSWORD
from timesheets.models import ChangeRequest, PeriodApproval, TimeEntry
from timesheets.services.approvals import approve_period

pytestmark = E2E
NEW_PASSWORD = "Brand-New-Pass-2026"
WEEK2 = PERIOD + timedelta(weeks=1)
MONDAY = THIS_WEEK + timedelta(days=1)  # weeks start on Sunday (D-111)


def week_url(week):
    return reverse("timesheet_week", args=[week])


def status_of(page):
    return page.locator("#week-status")


PORTAL = "PRJ-001 Customer Portal / Project work"


def cell(page, row, day):
    """A grid cell's button, e.g. cell(page, PORTAL, date(2026, 10, 19)) (D-106)."""
    name = re.escape(f"{row}, {day:%a %b %-d}:").replace("/", r"\/")  # Playwright: /…/ regex
    return page.get_by_role("button", name=re.compile(f"^{name}"))


def open_cell(page, row, day):
    cell(page, row, day).click()
    panel = page.locator("dialog[open]")
    expect(panel).to_be_visible()
    return panel


def add_row(page, category, project=None):
    page.get_by_role("button", name="+ Add row").click()
    panel = page.locator("dialog[open]")
    panel.get_by_label("Category").select_option(label=category)
    if project:
        panel.get_by_label("Project").select_option(label=project)
    panel.get_by_role("button", name="Add row", exact=True).click()


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
    add_row(page, "Project work", "PRJ-001 Customer Portal")
    panel = open_cell(page, PORTAL, MONDAY)
    panel.get_by_label("Start").fill("09:00")
    panel.get_by_label("End").fill("17:00")
    panel.get_by_label("Reason").fill("Login page")
    panel.get_by_role("button", name="Done").click()
    expect(cell(page, PORTAL, MONDAY)).to_have_text("8.00")
    page.get_by_role("button", name="Save draft").click()
    expect(status_of(page)).to_have_text("Draft")

    page.goto(week_url(THIS_WEEK))  # reopened: the slot is still there
    expect(cell(page, PORTAL, MONDAY)).to_have_text("8.00")
    panel = open_cell(page, PORTAL, MONDAY)
    expect(panel.get_by_label("Reason")).to_have_value("Login page")
    panel.get_by_role("button", name="Done").click()
    page.get_by_role("button", name="Submit").click()
    expect(status_of(page)).to_have_text("Submitted")
    expect(page.get_by_role("button", name="Save draft")).to_have_count(0)
    expect(page.locator("#entries input")).to_have_count(0)  # read-only now
    panel = open_cell(page, PORTAL, MONDAY)
    expect(panel).to_contain_text("Login page")
    expect(panel).to_contain_text("09:00")


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
    expect(page.locator("#entries input")).to_have_count(0)
    expect(page.locator("#entries")).to_contain_text("Feature work")


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
    panel.get_by_label("End").fill("18:00")
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
    expect(records.filter(has_text="Sep 27")).to_contain_text("40.00")
    expect(records.filter(has_text="Sep 27")).to_contain_text("2.00")  # overtime
    expect(records.filter(has_text="Oct 4")).to_contain_text("Current")


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
            panel.get_by_label("Reason").fill("Feature work and demo")
            panel.get_by_role("button", name="Done").click()
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


def test_weekly_grid_in_the_browser(e2e_org, make_week, open_as):
    """T-167: E2E grid: add rows, two slots by keyboard, live totals, unsaved warning, narrow."""
    page = open_as(e2e_org.dev1)
    page.goto(week_url(THIS_WEEK))
    add_row(page, "Project work", "PRJ-001 Customer Portal")
    add_row(page, "Project work", "PRJ-001 Customer Portal")  # a duplicate is refused
    expect(page.locator("dialog[open]")).to_contain_text("That row is already in the grid")
    page.locator("dialog[open]").get_by_role("button", name="Cancel").click()

    tuesday = THIS_WEEK + timedelta(days=2)
    button = cell(page, PORTAL, tuesday)
    button.focus()
    page.keyboard.press("Enter")  # cells are buttons: the keyboard opens them
    panel = page.locator("dialog[open]")
    panel.get_by_label("Start").fill("08:00")
    panel.get_by_label("End").fill("12:00")
    panel.get_by_label("Reason").fill("Bug fixes")
    expect(button).to_have_text("4.00")  # live while typing
    panel.get_by_role("button", name="+ Add time slot").click()
    panel.get_by_label("Start").nth(1).fill("13:00")
    panel.get_by_label("End").nth(1).fill("17:30")
    panel.get_by_label("Reason").nth(1).fill("Code review")
    page.keyboard.press("Escape")  # Esc closes; focus goes back to the cell
    expect(page.locator("dialog[open]")).to_have_count(0)
    expect(button).to_be_focused()
    expect(button).to_contain_text("8.50")
    expect(page.locator("#entries [data-role=week-total]")).to_have_text("8.50")

    add_row(page, "PTO")
    panel = open_cell(page, "PTO", tuesday + timedelta(days=1))
    panel.get_by_label("Hours").fill("8")
    panel.get_by_label("Reason").fill("Vacation")
    panel.get_by_role("button", name="Done").click()
    expect(page.locator("#entries [data-role=week-total]")).to_have_text("8.50")  # leave not in it

    warnings = []
    page.on("dialog", lambda dialog: warnings.append(dialog.type))
    page.get_by_role("link", name="Dashboard").click()  # unsaved changes: the browser asks first
    expect(page).to_have_url(re.compile(r"/$"))
    assert "beforeunload" in warnings
    page.goto(week_url(THIS_WEEK))
    assert TimeEntry.objects.count() == 0  # nothing was saved by leaving

    add_row(page, "Project work", "PRJ-001 Customer Portal")
    panel = open_cell(page, PORTAL, tuesday)
    panel.get_by_label("Start").fill("09:00")
    panel.get_by_label("End").fill("12:00")
    panel.get_by_label("Reason").fill("Bug fixes")
    panel.get_by_role("button", name="Done").click()
    page.get_by_role("button", name="Save draft").click()
    expect(status_of(page)).to_have_text("Draft")
    assert TimeEntry.objects.count() == 1

    page.set_viewport_size({"width": 390, "height": 844})
    scroller = page.locator(".grid-scroll")
    assert scroller.evaluate("e => e.scrollWidth > e.clientWidth")  # the grid scrolls sideways
    assert page.evaluate("() => { scrollTo(5000, 0); return scrollX; }") == 0  # the page doesn't
    first = page.locator("#entries tbody th.grid-label").first
    scroller.evaluate("e => e.scrollLeft = 300")
    assert first.evaluate("e => getComputedStyle(e).position") == "sticky"
    box = first.bounding_box()
    assert box["x"] < 20  # still at the left edge while the days scroll
