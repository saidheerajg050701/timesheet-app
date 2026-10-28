"""End-to-end fixtures (D-94): a live test server on the test databases, a fixed clock, and
one browser context per person. Never touches db.sqlite3 or payroll.sqlite3."""

import os
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
import time_machine
from playwright.sync_api import expect

from tests.factories import (
    TEST_PASSWORD,
    EmployeeFactory,
    ProjectFactory,
    TeamFactory,
    TimeEntryFactory,
    TimesheetFactory,
    UserFactory,
)

# Playwright's sync API runs an event loop in the test thread; Django's ORM refuses to run
# in a thread with a loop unless told it is safe. The browser runs in its own process.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

TZ = ZoneInfo("America/Chicago")
WEDNESDAY = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)  # the same fixed clock as tests/conftest.py
THIS_WEEK = date(2026, 10, 18)  # Sun 18 – Sat 24 Oct (D-111)
PERIOD = date(2026, 9, 27)  # the most recent completed pay period: Sep 27 + Oct 4
expect.set_options(timeout=10_000)


# Every e2e module sets: pytestmark = E2E
E2E = [pytest.mark.e2e, pytest.mark.django_db(transaction=True, databases=["default", "payroll"])]


@pytest.fixture
def clock():
    """Wednesday Oct 21 2026, 10:00 company time; the clock keeps ticking from there."""
    with time_machine.travel(WEDNESDAY, tick=True) as traveller:
        yield traveller


@pytest.fixture
def e2e_org(settings, clock):
    """A small company with accounts (password TEST_PASSWORD) and one sign-up candidate."""
    settings.COMPANY_EMAIL_DOMAIN = "@yourcompany.com"
    platform = TeamFactory(name="Platform", department="Technology")

    def person(code, first, last, manager=None, account=True, **extra):
        employee = EmployeeFactory(
            employee_code=code,
            email=f"{code.lower()}@yourcompany.com",
            first_name=first,
            last_name=last,
            manager=manager,
            team=platform,
            **extra,
        )
        if account:
            UserFactory(employee=employee)
        return employee

    ceo = person("CEO", "Asha", "Rao", is_admin=True, job_title="CEO")
    hr = person("HR", "Hana", "Reed", ceo, is_admin=True, job_title="HR Manager")
    manager = person("MANAGER", "Priya", "Shah", ceo, job_title="Engineering Manager")
    ops_manager = person("OPSMGR", "Omar", "Diaz", ceo, job_title="Operations Manager")
    return SimpleNamespace(
        ceo=ceo,
        hr=hr,
        manager=manager,
        dev1=person("DEV1", "John", "Kim", manager),
        dev2=person("DEV2", "Sara", "Ng", manager),
        ops_manager=ops_manager,
        ops1=person("OPS1", "Lena", "Park", ops_manager),
        payroll=person("PAYROLL", "Paul", "Ames", ceo, is_payroll=True),
        candidate=person("QA1", "Ravi", "Kumar", manager, account=False, job_title="QA Engineer"),
        project=ProjectFactory(number=1, name="Customer Portal"),
    )


@pytest.fixture
def make_week(e2e_org):
    """A week of 09:00–17:00 Project work rows (a longer Monday adds overtime)."""

    def make(employee, week, status="SUBMITTED", monday_end=time(17)):
        on_time = datetime.combine(week + timedelta(days=5), time(16), tzinfo=TZ)  # Friday
        sheet = TimesheetFactory(
            employee=employee,
            week_start=week,
            status=status,
            submitted_at=on_time if status != "DRAFT" else None,
        )
        for offset in range(5):
            end = monday_end if offset == 0 else time(17)
            TimeEntryFactory(
                timesheet=sheet,
                work_date=week + timedelta(days=1 + offset),  # Mon–Fri
                project=e2e_org.project,
                end_time=end,
                minutes=(end.hour - 9) * 60,
                reason="Feature work",
            )
        return sheet

    return make


@pytest.fixture
def open_as(browser, live_server):
    """A logged-in page for an employee, each in its own browser context (own cookies)."""
    contexts = []

    def _open(employee, password=TEST_PASSWORD):
        context = browser.new_context(base_url=live_server.url, accept_downloads=True)
        contexts.append(context)
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())  # "Submit this week?" etc.
        log_in(page, employee.email, password)
        expect(page.get_by_text(employee.employee_code, exact=False).first).to_be_visible()
        return page

    yield _open
    for context in contexts:
        context.close()


@pytest.fixture
def anonymous(browser, live_server):
    context = browser.new_context(base_url=live_server.url)
    page = context.new_page()
    page.on("dialog", lambda dialog: dialog.accept())
    yield page
    context.close()


def log_in(page, email, password):
    page.goto("/login/")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_load_state()
