"""Browser tests: payroll records, export, registers."""

from datetime import datetime, time
from pathlib import Path

from django.urls import reverse
from playwright.sync_api import expect

from apps.directory.models import Employee
from apps.timesheets.services.approvals import approve_period
from tests.e2e.conftest import E2E, PERIOD, TZ
from tests.e2e.helpers import WEEK2

pytestmark = E2E


def test_approve_then_payroll_sees_the_records(e2e_org, make_week, open_as):
    """T-150: E2E manager approves a period; the payroll user sees both week records — once
    everyone in the period is approved (Change 9: no hours while the register is OPEN)."""
    make_week(e2e_org.dev1, PERIOD, monday_end=time(19))  # 42 h: 2 h overtime
    make_week(e2e_org.dev1, WEEK2)
    for person in Employee.objects.exclude(pk=e2e_org.dev1.pk):  # the others, 0.00 weeks
        approver = person.manager or e2e_org.hr
        approve_period(approver, person, PERIOD, now=datetime.now(TZ), confirm_unsubmitted=True)
    payroll = open_as(e2e_org.payroll)
    payroll.goto(f"{reverse('payroll')}?period={PERIOD.isoformat()}")
    expect(payroll.locator("#payroll-records")).to_have_count(0)  # OPEN: John still pending

    manager = open_as(e2e_org.manager)
    manager.goto(reverse("approval_detail", args=[PERIOD, "DEV1"]))
    manager.get_by_role("button", name="Approve both weeks").click()
    expect(manager.get_by_role("alert")).to_have_text("Approved John's period.")

    payroll.reload()
    records = payroll.locator("#payroll-records tbody tr", has_text="John Kim")
    expect(records).to_have_count(2)
    expect(records.filter(has_text="Sep 27")).to_contain_text("40.00")
    expect(records.filter(has_text="Sep 27")).to_contain_text("2.00")  # overtime
    expect(records.filter(has_text="Oct 4")).to_contain_text("Current")


def test_payroll_export_and_mark_paid(e2e_org, make_week, open_as, clock):
    """T-152: E2E payroll finalizes & exports the period's register, downloads the detailed
    CSV, then marks it paid (D-135). Everyone else is approved too: since Change 9 a register
    is ready only then (D-142) — their never-submitted weeks with 0.00 hours."""
    make_week(e2e_org.dev1, PERIOD)
    make_week(e2e_org.dev1, WEEK2)
    for person in Employee.objects.all():  # publishes after each commit
        approver = person.manager or e2e_org.hr
        approve_period(approver, person, PERIOD, now=datetime.now(TZ), confirm_unsubmitted=True)
    page = open_as(e2e_org.payroll)
    page.goto(reverse("payroll_period", args=[PERIOD]))
    expect(page.locator("#register-status")).to_have_text("Ready")
    page.get_by_role("button", name="Finalize & export").click()
    page.locator("#finalize-dialog").get_by_role("button", name="Finalize & export").click()
    expect(page.get_by_role("alert")).to_contain_text("exported as batch EXP-0001")
    with page.expect_download() as download:
        page.get_by_role("link", name="Download detailed CSV").click()
    assert download.value.suggested_filename == (
        "payroll-detail_2026-09-27_to_2026-10-10_EXP-0001.csv"
    )
    text = Path(download.value.path()).read_text(encoding="utf-8-sig")
    assert text.startswith("batch,employee_code") and text.count("DEV1") == 2

    expect(page.locator("#payroll-records")).to_contain_text("Exported")
    page.get_by_role("button", name="Mark as paid").click()
    expect(page.locator("#register-status")).to_have_text("Paid")
    john = page.locator("#payroll-records tbody tr", has_text="John Kim")
    expect(john.filter(has_text="Paid")).to_have_count(2)


def test_register_from_last_approval_to_paid(e2e_org, make_week, open_as, clock):
    """T-216: E2E the register stays OPEN until the last approval, is READY right after it,
    then Finalize & export (one batch, downloads) and Mark as paid (D-132–D-135)."""
    clock.move_to(datetime(2026, 10, 12, 9, 0, tzinfo=TZ))  # Monday, before the 12:00 deadline
    people = list(Employee.objects.all())
    for person in people:
        make_week(person, PERIOD)
        make_week(person, WEEK2)
        if person != e2e_org.dev2:
            approver = person.manager or e2e_org.hr  # the CEO: approved by HR (D-11)
            approve_period(approver, person, PERIOD, now=datetime.now(TZ))
    payroll = open_as(e2e_org.payroll)
    payroll.goto(reverse("payroll_period", args=[PERIOD]))
    expect(payroll.locator("#register-status")).to_have_text("Open")
    pending = payroll.locator("#pending-by-manager")
    expect(pending).to_contain_text("Sara Ng")
    expect(pending).to_contain_text("Priya Shah")  # her approver
    expect(payroll.get_by_role("button", name="Finalize & export")).to_have_count(0)  # OPEN

    manager = open_as(e2e_org.manager)
    manager.goto(reverse("approval_detail", args=[PERIOD, "DEV2"]))
    manager.get_by_role("button", name="Approve both weeks").click()
    expect(manager.get_by_role("alert")).to_have_text("Approved Sara's period.")

    payroll.reload()
    expect(payroll.locator("#register-status")).to_have_text("Ready")
    expect(payroll.locator("#ready-reason")).to_contain_text("Everyone who must be approved")
    payroll.get_by_role("button", name="Finalize & export").click()
    payroll.locator("#finalize-dialog").get_by_role("button", name="Finalize & export").click()
    expect(payroll.get_by_role("alert")).to_contain_text("exported as batch EXP-0001")
    expect(payroll.locator("#register-status")).to_have_text("Finalized & exported")
    expect(payroll.locator("#register tbody tr")).to_have_count(len(people))
    with payroll.expect_download() as download:
        payroll.get_by_role("link", name="Download register CSV").click()
    assert download.value.suggested_filename == (
        "payroll-register_2026-09-27_to_2026-10-10_EXP-0001.csv"
    )
    lines = Path(download.value.path()).read_text(encoding="utf-8-sig").splitlines()
    assert lines[0].startswith("employee_code,") and len(lines) == len(people) + 1

    payroll.get_by_role("button", name="Mark as paid").click()
    expect(payroll.locator("#register-status")).to_have_text("Paid")
    expect(payroll.get_by_role("button", name="Mark as paid")).to_have_count(0)
    payroll.goto(reverse("payroll"))
    row = payroll.locator('#pay-periods tr[data-period="2026-09-27"]')
    expect(row).to_contain_text("Paid")
    expect(row).to_contain_text(f"{len(people)} of {len(people)}")
    expect(row).to_contain_text("EXP-0001")
