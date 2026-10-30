"""Browser tests: HR in Admin — deactivate, password reset."""

import re

from django.urls import reverse
from playwright.sync_api import expect

from tests.e2e.conftest import E2E, log_in
from tests.e2e.helpers import (
    NEW_PASSWORD,
)
from tests.factories import (
    TEST_PASSWORD,
)

pytestmark = E2E


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
