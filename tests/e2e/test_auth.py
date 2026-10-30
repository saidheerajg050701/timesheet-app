"""Browser tests: sign-up and pages people may not open."""

from django.urls import reverse
from playwright.sync_api import expect

from apps.timesheets.models import PeriodApproval
from tests.e2e.conftest import E2E
from tests.e2e.helpers import (
    NEW_PASSWORD,
)

pytestmark = E2E


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
