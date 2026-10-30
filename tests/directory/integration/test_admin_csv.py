import csv
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.directory.models import Employee

IMPORT = "admin:directory_employee_import"
EXPORT = "admin:directory_employee_export"


@pytest.fixture(autouse=True)
def company_domain(settings):
    settings.COMPANY_EMAIL_DOMAIN = "@yourcompany.com"


def upload(client, text):
    file = SimpleUploadedFile("employees.csv", text.encode("utf-8"), content_type="text/csv")
    return client.post(reverse(IMPORT), {"file": file})


def exported(client, **params):
    response = client.get(reverse(EXPORT), params)
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    return response.content.decode("utf-8-sig")


def edit(text, code, **changes):
    """The CSV text with one employee's cells changed (or a new row when code is unknown)."""
    rows = list(csv.DictReader(io.StringIO(text)))
    columns = list(rows[0])
    target = next((r for r in rows if r["employee_code"] == code), None)
    if target is None:
        target = dict.fromkeys(columns, "") | {"employee_code": code}
        rows.append(target)
    target.update(changes)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def snapshot():
    return list(Employee.objects.order_by("pk").values())


def test_csv_import_in_admin(org, login_as):
    """T-142: errors with line numbers, a preview that changes nothing, then all-or-nothing."""
    client = login_as(org.hr)
    original = exported(client)
    before, audit_rows = snapshot(), AuditLog.objects.count()

    bad = edit(original, "DEV1", status="GONE")
    bad = edit(bad, "NEW1", email="new1@yourcompany.com", manager_code="NOPE")
    page = upload(client, bad).content.decode()
    assert 'id="import-errors"' in page and "Nothing was imported" in page
    line = 1 + 1 + [r["employee_code"] for r in csv.DictReader(io.StringIO(original))].index("DEV1")
    assert f"Line {line}: status must be ACTIVE or INACTIVE" in page
    assert "first_name is required" in page  # cross-file checks run once every row parses

    good = edit(original, "DEV1", job_title="Staff Engineer")
    good = edit(
        good,
        "NEW1",
        email="new1@yourcompany.com",
        first_name="Nia",
        last_name="New",
        job_title="Analyst",
        manager_code="MANAGER",
        status="ACTIVE",
        is_admin="false",
        is_payroll="false",
    )
    preview = upload(client, good)
    result = preview.context["preview"]
    assert (result.created, result.updated) == (1, 1)
    assert (
        "DEV1",
        "updated",
        {"job_title": ("Software Engineer", "Staff Engineer")},
    ) in result.changes
    assert "Nothing has changed yet" in preview.content.decode()
    assert snapshot() == before and AuditLog.objects.count() == audit_rows  # dry run only

    tampered = client.post(
        reverse(IMPORT), {"confirm": "1", "payload": "x" + preview.context["payload"]}
    )
    assert tampered.status_code == 302 and snapshot() == before

    client.post(reverse(IMPORT), {"confirm": "1", "payload": preview.context["payload"]})
    assert Employee.objects.get(employee_code="DEV1").job_title == "Staff Engineer"
    assert Employee.objects.get(employee_code="NEW1").manager == org.manager
    new_rows = AuditLog.objects.filter(entity_type="Employee", action__in=["CREATE", "UPDATE"])
    assert {(r.action, r.entity_id, r.actor_id) for r in new_rows} == {
        ("UPDATE", "DEV1", org.hr.pk),
        ("CREATE", "NEW1", org.hr.pk),
    }

    current = snapshot()
    looping = edit(exported(client), "DIRECTOR", manager_code="DEV1", job_title="Changed")
    looping = edit(looping, "HR", is_admin="false", status="INACTIVE")
    looping = edit(looping, "MANAGER", status="INACTIVE", end_date="2026-10-16")
    looping = edit(looping, "OPS1", email="ops1@gmail.com")
    page = upload(client, looping).content.decode()
    assert "makes a reporting loop" in page and "you cannot remove your own admin flag" in page
    assert "you cannot deactivate yourself" in page and "MANAGER still manages active" in page
    assert "ops1@gmail.com is not a company email address" in page
    assert "<form" in page and 'name="confirm"' not in page
    assert snapshot() == current


def test_csv_export_round_trip(org, login_as):
    """T-143: export → import changes nothing; formula cells are escaped and come back as is."""
    Employee.objects.filter(pk=org.dev1.pk).update(job_title="=HYPERLINK(1)", location="+44")
    client = login_as(org.hr)
    text = exported(client)
    rows = {r["employee_code"]: r for r in csv.DictReader(io.StringIO(text))}
    assert list(next(iter(rows.values()))) == [
        "employee_code",
        "email",
        "first_name",
        "last_name",
        "job_title",
        "team",
        "department",
        "manager_code",
        "location",
        "hire_date",
        "is_admin",
        "is_payroll",
        "status",
        "end_date",
    ]
    assert rows["DEV1"]["job_title"] == "'=HYPERLINK(1)" and rows["DEV1"]["location"] == "'+44"
    assert rows["DEV1"]["manager_code"] == "MANAGER" and rows["CEO"]["is_admin"] == "true"
    assert len(rows) == Employee.objects.count()

    result = upload(client, text).context["preview"]
    assert (result.created, result.updated, result.unchanged) == (0, 0, len(rows))
    assert result.changes == []

    [row] = AuditLog.objects.filter(action="EXPORT")
    assert row.actor == org.hr and row.after == {"rows": len(rows)}
    payroll_only = exported(client, is_payroll__exact=1)
    assert {r["employee_code"] for r in csv.DictReader(io.StringIO(payroll_only))} == {
        "FINANCE",
        "PAYROLL",
    }
