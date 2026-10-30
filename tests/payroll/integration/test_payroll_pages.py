import csv
import io
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.payroll.models import PayrollRegister, PayrollWeek
from apps.payroll.services.export import export_period, safe_cell
from apps.payroll.services.publish import supersede_week
from apps.payroll.services.register import finalize, period_items
from apps.timesheets.models import ChangeRequest
from apps.timesheets.services.approvals import approve_period
from tests.factories import EmployeeFactory

pytestmark = pytest.mark.django_db(databases=["default", "payroll"])

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)
PERIOD = date(2026, 9, 27)  # weeks of Sun Sep 27 + Oct 4
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


DETAIL = "payroll-detail_2026-09-27_to_2026-10-10_EXP-0001.csv"


def test_export_csv(org, approved, approve_everyone, login_as):
    """T-37: Finalize & export: the detailed CSV is correct; records EXPORTED in one numbered
    batch (since Change 8 the register's only batch, D-135)."""
    approved(org.dev1, org.dev2)
    approve_everyone(PERIOD, NOW)  # READY only once everyone is approved (D-142)
    client = login_as(org.payroll)
    response = client.post(reverse("payroll_finalize", args=[PERIOD]))
    assert response.url == reverse("payroll_period", args=[PERIOD])
    download = client.get(reverse("payroll_detail_csv", args=[PERIOD]))
    assert download["Content-Type"] == "text/csv; charset=utf-8"
    assert f'filename="{DETAIL}"' in download["Content-Disposition"]
    everything = read_csv(download)
    rows = [r for r in everything if r["employee_code"].startswith("DEV")]  # others: 0.00 weeks
    assert [(r["employee_code"], r["week_start"]) for r in rows] == [
        ("DEV1", "2026-09-27"),
        ("DEV1", "2026-10-04"),
        ("DEV2", "2026-09-27"),
        ("DEV2", "2026-10-04"),
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

    again = client.post(reverse("payroll_finalize", args=[PERIOD]))
    assert "already finalized" in client.get(again.url).content.decode()
    assert read_csv(client.get(reverse("payroll_detail_csv", args=[PERIOD]))) == everything
    assert PayrollRegister.objects.get().export_batch == "EXP-0001"

    newcomer = EmployeeFactory(  # added later with a start date inside the finalized period
        employee_code="LATE1", manager=org.manager, hire_date=PERIOD + timedelta(days=1)
    )
    approved(newcomer, period=PERIOD)  # approved after finalizing → the next register (D-136)
    late = period_items(PERIOD + timedelta(weeks=2)).late
    assert [(r.employee_code, r.status) for r in late] == [("LATE1", "CURRENT")] * 2


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
    org, make_week, login_as, approve_everyone, django_capture_on_commit_callbacks
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
    approve_everyone(PERIOD, NOW)
    client.post(reverse("payroll_finalize", args=[PERIOD]))
    rows = [
        r
        for r in read_csv(client.get(reverse("payroll_detail_csv", args=[PERIOD])))
        if r["employee_code"] == "RISK1"
    ]
    assert rows[0]["employee_name"] == '\'=HYPERLINK("x") @evil'
    assert rows[0]["batch"] == "EXP-0001" and rows[0]["regular_hours"] == "40.00"


def test_who_can_open_payroll_pages(org, approved, approve_everyone, login_as):
    """T-111: payroll users and admins only; payroll never opens other people's timesheets."""
    approved(org.dev1)
    approve_everyone(PERIOD, NOW)
    finalize(PERIOD, system_actor="test", now=NOW)
    gets = [
        reverse("payroll"),
        reverse("payroll_period", args=[PERIOD]),
        reverse("payroll_corrections"),
        reverse("payroll_batch_csv", args=["EXP-0001"]),
        reverse("payroll_register_csv", args=[PERIOD]),
        reverse("payroll_detail_csv", args=[PERIOD]),
        reverse("payroll_registers_csv"),
    ]
    posts = [
        reverse("payroll_finalize", args=[PERIOD]),
        reverse("payroll_register_paid", args=[PERIOD]),
    ]
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
    sheet = PayrollWeek.objects.get(employee_code="DEV1", week_start=PERIOD).source_timesheet_id
    change = ChangeRequest.objects.create(timesheet_id=sheet, requester=org.dev1, reason="x")
    for url in (
        reverse("team_member", args=["DEV1"]),
        reverse("approval_detail", args=[PERIOD, "DEV1"]),
        reverse("request_detail", args=[change.pk]),
    ):
        assert client.get(url).status_code == 403, url
    for url in (reverse("payroll"), reverse("payroll_period", args=[PERIOD])):
        page = client.get(url).content.decode()
        assert "Feature development" not in page  # entry reasons never appear on payroll pages


def records_of(html):
    """Employee names in the period page's Week records table."""
    table = html.split('id="payroll-records"')[1].split("</table>")[0]
    return re.findall(r"<tr>\s*<td>([^<]+)</td>", table)


def test_payroll_page_filters_and_totals(org, approved, approve_everyone, login_as):
    """Helper check: the period's week records with filters; hours with 2 decimals. While
    OPEN no hours are shown at all (Change 9, D-142)."""
    approved(org.dev1, org.ops1)
    client = login_as(org.payroll)
    url = reverse("payroll_period", args=[PERIOD])
    page = client.get(url).content.decode()
    assert 'id="register"' not in page and 'id="payroll-records"' not in page  # OPEN
    approve_everyone(PERIOD, NOW)  # READY: the others' never-submitted weeks at 0.00
    page = client.get(url).content.decode()
    assert len(records_of(page)) == 20 and records_of(page).count("Lena Park") == 2
    assert "80.00" in page.split('<tr data-employee="DEV1">')[1].split("</tr>")[0]
    filtered = client.get(url, {"team": "Platform"}).content.decode()
    assert set(records_of(filtered)) == {"John Kim", "Sara Ng", "Priya Shah"}
    department = client.get(url, {"department": "Technology"}).content.decode()
    assert {"John Kim", "Lena Park"} <= set(records_of(department))
    assert len(records_of(client.get(url, {"employee": "kim"}).content.decode())) == 2
    exported = client.get(url, {"status": "EXPORTED"}).content.decode()
    assert records_of(exported) == [] and "No records." in exported
    assert client.get(reverse("payroll"), {"period": "nope"}).status_code == 404


def test_mark_paid_from_the_page(org, approved, approve_everyone, login_as):
    """Helper check: the Mark as paid button pays the register's batch and returns to it."""
    approved(org.dev1)
    approve_everyone(PERIOD, NOW)
    client = login_as(org.payroll)
    client.post(reverse("payroll_finalize", args=[PERIOD]))
    response = client.post(reverse("payroll_register_paid", args=[PERIOD]))
    assert response.url == reverse("payroll_period", args=[PERIOD])
    assert set(PayrollWeek.objects.values_list("status", flat=True)) == {"PAID"}
    assert "Register marked as paid." in client.get(response.url).content.decode()
    again = client.post(reverse("payroll_register_paid", args=[PERIOD]))
    assert "already paid" in client.get(again.url).content.decode()
    assert client.get(reverse("payroll_batch_csv", args=["EXP-9999"])).status_code == 404
