"""Visual review (Change 1, D-105): screenshots of the main pages, not part of test_all.sh.

    SCREENSHOTS_DIR=/some/folder/outside/the/repo \\
        uv run pytest scripts/visual_review --browser-channel chrome

Starts a live test server on the TEST databases, builds the demo company there with
seed_demo (fixed clock: Wed Oct 21 2026, 10:00), logs in as an employee, a manager, payroll
and HR, and saves full-page screenshots at a laptop and a phone width. It never touches
db.sqlite3 or payroll.sqlite3.
"""

import os
from datetime import date, datetime, time
from io import StringIO
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.core.management import call_command
from django.urls import reverse

from directory.models import Employee
from timesheets.models import ChangeRequest, Project, TimeEntry, Timesheet

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")  # Playwright's sync API (D-94)

PASSWORD = "Visual-Review-Pass-2026"
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=ZoneInfo("America/Chicago"))
PERIOD = date(2026, 9, 27)  # most recent completed period: still pending in the demo data
PAID_PERIOD = date(2026, 9, 13)  # approved and published: payroll has records
SIZES = {"desktop": {"width": 1440, "height": 900}, "narrow": {"width": 390, "height": 844}}
OUT = os.environ.get("SCREENSHOTS_DIR")
# Can the page itself be scrolled sideways? Wide tables must scroll inside their own box.
OVERFLOW_JS = """() => {
  window.scrollTo(100000, window.scrollY);
  const scrolled = window.scrollX;
  window.scrollTo(0, window.scrollY);
  return scrolled;
}"""


def pages():
    """(who, file name, url) for every screenshot; who=None is a visitor."""
    dev1_week = reverse("timesheet_week", args=[date(2026, 10, 18)])
    past_week = reverse("timesheet_week", args=[date(2026, 10, 4)])
    approval = reverse("approval_detail", args=[PERIOD, "EMP-0004"])
    open_request = ChangeRequest.objects.filter(status="OPEN").first()
    return [
        (None, "login", reverse("login")),
        (None, "signup", reverse("signup")),
        ("dev1", "dashboard", reverse("home")),
        ("dev1", "timesheets", reverse("timesheets")),
        ("dev1", "week-current", dev1_week),
        ("dev1", "week-current-dialog", dev1_week),  # a cell's time slots, open
        ("dev1", "week-submitted", past_week),
        ("dev1", "requests", reverse("requests")),
        ("dev1", "profile", reverse("profile")),
        ("dev1", "403", reverse("team")),
        ("dev1", "404", "/no-such-page/"),
        ("eng.manager", "dashboard", reverse("home")),
        ("eng.manager", "team", reverse("team")),
        ("eng.manager", "team-member", reverse("team_member", args=["EMP-0004"])),
        ("eng.manager", "approvals", f"{reverse('approvals')}?period={PERIOD.isoformat()}"),
        ("eng.manager", "approval-detail", approval),
        ("eng.manager", "edit-directly", reverse("request_edit", args=[open_request.pk])),
        ("eng.manager", "change-requests", reverse("request_inbox")),
        ("payroll", "payroll", f"{reverse('payroll')}?period={PAID_PERIOD.isoformat()}"),
        ("payroll", "corrections", reverse("payroll_corrections")),
        ("hr", "dashboard", reverse("home")),
        ("hr", "team", reverse("team")),
        ("hr", "admin", reverse("admin:index")),
        ("hr", "admin-employees", reverse("admin:directory_employee_changelist")),
    ]


def draft_week():
    """dev1's current week as a draft with a few slots (the demo leaves it empty, D-27)."""
    dev1 = Employee.objects.get(employee_code="EMP-0004")
    portal, mobile = Project.objects.order_by("code")[:2]
    sheet = Timesheet.objects.create(employee=dev1, week_start=date(2026, 10, 18))
    rows = [
        (19, "PROJECT", portal, time(9), time(12), "Login page"),
        (19, "BREAK", None, time(12), time(12, 30), "Lunch"),
        (19, "PROJECT", portal, time(12, 30), time(15), "Code review"),
        (19, "MEETING", None, time(15), time(15, 30), "Stand-up"),
        (19, "PROJECT", mobile, time(15, 30), time(17), "Push notifications"),
        (20, "PROJECT", portal, time(8, 30), time(12), "Bug fixes"),
        (20, "BREAK", None, time(12), time(12, 45), "Lunch"),
        (20, "PROJECT", mobile, time(12, 45), time(17), "Release prep"),
        (21, "PTO", None, None, None, "Half day off"),
    ]
    for day, category, project, start, end, reason in rows:
        minutes = 240 if start is None else (end.hour - start.hour) * 60 + end.minute - start.minute
        TimeEntry.objects.create(
            timesheet=sheet, work_date=date(2026, 10, day), category=category, project=project,
            start_time=start, end_time=end, minutes=minutes, reason=reason,
        )  # fmt: skip


@pytest.mark.skipif(not OUT, reason="set SCREENSHOTS_DIR to a folder outside the repository")
@pytest.mark.django_db(transaction=True, databases=["default", "payroll"])
def test_screenshots(live_server, browser, settings):
    settings.DEMO_PASSWORD = PASSWORD
    settings.PAY_PERIOD_ANCHOR = date(2026, 1, 4)  # a Sunday, whatever .env says (D-113)
    settings.COMPANY_EMAIL_DOMAIN = "@yourcompany.com"
    out = Path(OUT)
    out.mkdir(parents=True, exist_ok=True)
    with time_machine.travel(NOW, tick=True):
        call_command("seed_demo", stdout=StringIO())
        draft_week()
        for size, viewport in SIZES.items():
            contexts = {}
            for who, name, url in pages():
                if who not in contexts:
                    context = browser.new_context(base_url=live_server.url, viewport=viewport)
                    context.clock.install(time=NOW)  # the browser's countdowns use the same clock
                    page = context.new_page()
                    if who:
                        page.goto(reverse("login"))
                        page.get_by_label("Email").fill(f"{who}@yourcompany.com")
                        page.get_by_label("Password").fill(PASSWORD)
                        page.get_by_role("button", name="Log in").click()
                        page.wait_for_url(lambda u: "/login/" not in u)
                    contexts[who] = page
                page = contexts[who]
                response = page.goto(url)
                expected = int(name) if name in ("403", "404") else 200
                assert response.status == expected, (who, name, response.status)
                page.wait_for_load_state("networkidle")
                overflow = page.evaluate(OVERFLOW_JS)
                assert not overflow, (size, who, name)  # tables scroll, the page never does
                if name.endswith("-dialog"):
                    page.locator("#entries .cell-button:has(.cell-count)").first.click()
                    page.locator("dialog[open]").wait_for()
                path = out / f"{size}-{who or 'visitor'}-{name}.png"
                if name.endswith("-dialog"):  # a modal covers the window, not the whole page
                    page.screenshot(path=path)
                    continue
                height = page.evaluate("document.documentElement.scrollHeight")
                page.screenshot(
                    path=path,
                    full_page=True,
                    clip={"x": 0, "y": 0, "width": viewport["width"], "height": height},
                )
            for page in contexts.values():
                page.context.close()
