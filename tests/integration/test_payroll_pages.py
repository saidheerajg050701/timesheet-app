import csv
import io
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse

from audit.models import AuditLog
from payroll.models import PayrollWeek
from payroll.services.export import export_period, safe_cell
from payroll.services.publish import supersede_week
from tests.factories import EmployeeFactory
from timesheets.models import ChangeRequest
from timesheets.services.approvals import approve_period

pytestmark = pytest.mark.django_db(databases=["default", "payroll"])

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)
PERIOD = date(2026, 9, 28)
WEEK1, WEEK2 = PERIOD, PERIOD + timedelta(weeks=1)


@pytest.fixture
def approved(org, make_week, django_capture_on_commit_callbacks):
    """Approve a full period (2 × 40 h) for each given employee; payroll written after commit."""

    def _approved(*people, period=PERIOD):
        for person in people:
            make_week(person, period)
            make_week(person, period + timedelta(weeks=1))
            with django_capture_on_commit_callbacks(execute=True):
                approve_period(person.manager, person, period, now=NOW)

    return _approved


def read_csv(response):
    text = b"".join(response.streaming_content if response.streaming else [response.content])
    return list(csv.DictReader(io.StringIO(text.decode("utf-8-sig"))))


def test_export_csv(org, approved, login_as):
    """T-37: Export CSV: correct contents; records EXPORTED with a sequential batch number."""
    approved(org.dev1, org.dev2)
    client = login_as(org.payroll)
    response = client.post(reverse("payroll_export"), {"period": PERIOD.isoformat()})
    assert response.url == reverse("payroll_batch_csv", args=["EXP-0001"])
    download = client.get(response.url)
    assert download["Content-Type"] == "text/csv; charset=utf-8"
    assert 'filename="payroll-EXP-0001.csv"' in download["Content-Disposition"]
    rows = read_csv(download)
    assert [(r["employee_code"], r["week_start"]) for r in rows] == [
        ("DEV1", "2026-09-28"),
        ("DEV1", "2026-10-05"),
        ("DEV2", "2026-09-28"),
        ("DEV2", "2026-10-05"),
    ]
    first = rows[0]
    assert (first["regular_hours"], first["overtime_hours"], first["total_hours"]) == (
        "40.00",
        "0.00",
        "40.00",
    )
    assert first["batch"] == "EXP-0001" and first["approved_by"].endswith(org.manager.last_name)
    assert set(PayrollWeek.objects.values_list("status", "export_batch")) == {
        ("EXPORTED", "EXP-0001")
    }
    assert AuditLog.objects.get(action="EXPORT").actor == org.payroll

    again = client.post(reverse("payroll_export"), {"period": PERIOD.isoformat()})
    assert "Nothing new to export" in client.get(again.url).content.decode()
    assert read_csv(client.get(response.url)) == rows  # re-download changes nothing

    approved(org.ops1, period=PERIOD)  # a new approval in the same period → next batch
    assert client.post(reverse("payroll_export"), {"period": PERIOD.isoformat()}).url.endswith(
        "EXP-0002.csv"
    )


def test_managers_and_employees_get_403(org, login_as):
    """T-38: a manager or an employee opening /payroll/ gets 403."""
    for person in (org.manager, org.dev1):
        assert login_as(person).get(reverse("payroll")).status_code == 403


def test_superseded_after_export_is_listed_in_corrections(org, approved, login_as):
    """T-39: a week superseded after it was exported is listed in Corrections."""
    approved(org.dev1)
    export_period(PERIOD, system_actor="test", at=NOW)
    supersede_week("DEV1", WEEK1, system_actor="test", at=NOW + timedelta(days=1))
    html = login_as(org.payroll).get(reverse("payroll_corrections")).content.decode()
    assert 'data-employee="DEV1"' in html and "waiting for re-approval" in html
    assert "Exported (EXP-0001)" in html and "−40.00" in html
    assert html.count("<tr data-employee=") == 1  # the CURRENT/never-exported week isn't listed


def test_csv_cells_are_spreadsheet_safe(
    org, make_week, login_as, django_capture_on_commit_callbacks
):
    """T-110: cells starting with = + - @ are escaped with a leading '; batches are sequential."""
    assert [safe_cell(v) for v in ("=SUM(A1)", "+1", "-2", "@cmd", "\tx", "Ok", "7.50")] == [
        "'=SUM(A1)",
        "'+1",
        "'-2",
        "'@cmd",
        "'\tx",
        "Ok",
        "7.50",
    ]
    risky = EmployeeFactory(
        manager=org.manager, first_name='=HYPERLINK("x")', last_name="@evil", employee_code="RISK1"
    )
    make_week(risky, WEEK1)
    make_week(risky, WEEK2)
    with django_capture_on_commit_callbacks(execute=True):
        approve_period(org.manager, risky, PERIOD, now=NOW)
    client = login_as(org.payroll)
    response = client.post(reverse("payroll_export"), {"period": PERIOD.isoformat()})
    rows = read_csv(client.get(response.url))
    assert rows[0]["employee_name"] == '\'=HYPERLINK("x") @evil'
    assert rows[0]["batch"] == "EXP-0001" and rows[0]["regular_hours"] == "40.00"


def test_who_can_open_payroll_pages(org, approved, login_as):
    """T-111: payroll users and admins only; payroll never opens other people's timesheets."""
    approved(org.dev1)
    export_period(PERIOD, system_actor="test", at=NOW)
    gets = [
        reverse("payroll"),
        reverse("payroll_corrections"),
        reverse("payroll_batch_csv", args=["EXP-0001"]),
    ]
    posts = [reverse("payroll_export"), reverse("payroll_mark_paid", args=["EXP-0001"])]
    for person in (org.payroll, org.finance, org.hr):  # payroll flag, payroll+manager, admin
        client = login_as(person)
        assert all(client.get(url).status_code == 200 for url in gets), person.employee_code
    for person in (org.dev1, org.manager, org.director):
        client = login_as(person)
        for url in gets:
            assert client.get(url).status_code == 403, (person.employee_code, url)
        for url in posts:
            assert client.post(url, {"period": PERIOD.isoformat()}).status_code == 403
    assert PayrollWeek.objects.filter(status="PAID").count() == 0

    # D-12: the payroll flag adds payroll pages only — never timesheet details of others.
    client = login_as(org.payroll)
    sheet = PayrollWeek.objects.first().source_timesheet_id
    change = ChangeRequest.objects.create(timesheet_id=sheet, requester=org.dev1, reason="x")
    for url in (
        reverse("team_member", args=["DEV1"]),
        reverse("approval_detail", args=[PERIOD, "DEV1"]),
        reverse("request_detail", args=[change.pk]),
    ):
        assert client.get(url).status_code == 403, url
    page = client.get(reverse("payroll")).content.decode()
    assert "Feature development" not in page  # entry reasons never appear on payroll pages


def test_payroll_page_filters_and_totals(org, approved, make_week, login_as):
    """Helper check: totals per employee for the period, with filters; hours with 2 decimals."""
    approved(org.dev1, org.ops1)
    client = login_as(org.payroll)
    page = client.get(reverse("payroll")).content.decode()  # newest period with records
    assert page.count("<tr data-employee=") == 2 and "80.00" in page
    filtered = client.get(reverse("payroll"), {"team": "Platform"}).content.decode()
    assert 'data-employee="DEV1"' in filtered and 'data-employee="OPS1"' not in filtered
    department = client.get(reverse("payroll"), {"department": "Technology"}).content.decode()
    assert department.count("<tr data-employee=") == 2  # both factory employees are Technology
    by_name = client.get(reverse("payroll"), {"employee": "kim"}).content.decode()
    assert by_name.count("<tr data-employee=") == 1
    exported = client.get(reverse("payroll"), {"status": "EXPORTED"}).content.decode()
    assert "No payroll records match." in exported
    assert client.get(reverse("payroll"), {"period": "nope"}).status_code == 404


def test_mark_paid_from_the_page(org, approved, login_as):
    """Helper check: the Mark as paid button pays the batch and returns to its period."""
    approved(org.dev1)
    client = login_as(org.payroll)
    client.post(reverse("payroll_export"), {"period": PERIOD.isoformat()})
    response = client.post(reverse("payroll_mark_paid", args=["EXP-0001"]))
    assert response.url == f"{reverse('payroll')}?period={PERIOD.isoformat()}"
    assert set(PayrollWeek.objects.values_list("status", flat=True)) == {"PAID"}
    assert "2 week record(s) marked as paid" in client.get(response.url).content.decode()
    assert client.get(reverse("payroll_batch_csv", args=["EXP-9999"])).status_code == 404
