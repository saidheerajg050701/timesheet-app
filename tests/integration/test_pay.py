"""Change 12: employee pay (D-166, D-167) and project budgets in Admin (D-168). Pay is
admin-only history: a pay change, or a same-date correction, is a new record; nothing is
edited or deleted; every change is audited."""

import csv
import io
from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from audit.models import AuditLog
from directory.models import PayHistoryError, PayRecord
from directory.services.pay import (
    add_pay,
    check_pay,
    labour_cost,
    money,
    rate_index,
    record_on,
    suggested_hourly,
)
from timesheets.models import Project

TODAY = date(2026, 10, 21)


def pay(employee, rate, start=date(2024, 1, 8), salary=None):
    return PayRecord.objects.create(
        employee=employee,
        pay_type="SALARIED" if salary else "HOURLY",
        annual_salary=Decimal(salary) if salary else None,
        hourly_rate=Decimal(rate),
        effective_from=start,
        system_actor="test",
    )


def admin_url(name, *args):
    return reverse(f"admin:directory_employee_{name}", args=args)


def test_pay_records(org):
    """T-258: salaried and hourly records; suggested hourly = salary ÷ 2,080 to the cent; the
    record in force by date, a same-date correction wins; back-dating allowed but not before
    the hire date; history is never changed or deleted; exact cents (D-166)."""
    assert suggested_hourly(Decimal("85000")) == Decimal("40.87")
    assert suggested_hourly(Decimal("104000")) == Decimal("50.00")
    assert suggested_hourly(Decimal("100001")) == Decimal("48.08")  # 48.0773… rounds half-up
    assert money("$85,000") == Decimal("85000.00") and money(" ") is None
    assert labour_cost(15, Decimal("33.33")) == Decimal("8.33")  # 8.3325
    assert labour_cost(450, Decimal("41.11")) == Decimal("308.33")  # 7.5 h → 308.325
    with pytest.raises(ValueError):
        money("abc")

    first = add_pay(
        org.hr, org.dev1, "SALARIED", Decimal("104000"), None, date(2024, 2, 1), today=TODAY
    )
    assert (first.hourly_rate, first.annual_salary) == (Decimal("50.00"), Decimal("104000.00"))
    raise_ = add_pay(
        org.hr, org.dev1, "HOURLY", None, Decimal("61.25"), date(2026, 9, 29), today=TODAY
    )
    fix = add_pay(
        org.hr, org.dev1, "HOURLY", None, Decimal("62.00"), date(2026, 9, 29), today=TODAY
    )
    records = rate_index([org.dev1.pk])[org.dev1.pk]
    assert record_on(records, date(2024, 1, 31)) is None  # before any pay
    assert record_on(records, date(2026, 9, 28)) == first
    assert record_on(records, date(2026, 9, 29)) == fix != raise_  # the correction wins
    back = add_pay(org.hr, org.dev1, "HOURLY", None, Decimal("55"), date(2025, 1, 1), today=TODAY)
    assert record_on(rate_index([org.dev1.pk])[org.dev1.pk], date(2025, 6, 1)) == back

    errors = check_pay(org.dev1, "SALARIED", None, None, date(2023, 1, 1))
    assert set(errors) == {"annual_salary", "effective_from"}
    assert "before the hire date" in errors["effective_from"][0]
    assert set(check_pay(org.dev1, "HOURLY", Decimal("5"), None, TODAY)) == {
        "annual_salary",
        "hourly_rate",
    }
    assert set(check_pay(org.dev1, "OTHER", None, Decimal("1"), TODAY)) == {"pay_type"}
    assert not any("104000" in m for ms in errors.values() for m in ms)  # never an amount
    with pytest.raises(ValueError):
        add_pay(org.hr, org.dev1, "HOURLY", None, Decimal("0"), TODAY, today=TODAY)
    with pytest.raises(PayHistoryError):
        first.hourly_rate = Decimal("1")
        first.save()
    with pytest.raises(PayHistoryError):
        first.delete()
    with pytest.raises(PayHistoryError):
        PayRecord.objects.filter(pk=first.pk).update(hourly_rate=1)
    with pytest.raises(PayHistoryError):
        PayRecord.objects.all().delete()
    assert str(first) == f"Pay of {org.dev1.employee_code} from 2024-02-01"  # no amount
    rows = AuditLog.objects.filter(entity_type="Pay").order_by("pk")
    assert rows.count() == 4 and {r.actor for r in rows} == {org.hr}
    assert rows[0].before is None and rows[0].after["annual_salary"] == "104000.00"
    assert rows[1].before["hourly_rate"] == "50.00" and rows[1].after["hourly_rate"] == "61.25"
    assert rows[2].after["correction"] is True and rows[1].after["correction"] is False


def test_admin_pay_page(org, login_as, fixed_now):
    """T-259: only admins open the pay page; it shows the current pay and the history; Add
    pay change (the suggested rate when left empty) is audited; nothing can be deleted; pay is
    not in the employee list, the employee CSV or the Profile (D-167)."""
    pay(org.dev1, "50.00", salary="104000")
    client = login_as(org.hr)
    page = client.get(admin_url("pay", org.dev1.pk)).content.decode()
    assert "Current pay" in page and "$50.00 an hour" in page and "$104,000.00 a year" in page
    assert "Add pay change" in page and "Suggested:" in page  # the hint (filled by the page)
    response = client.post(
        admin_url("pay", org.dev1.pk),
        {
            "pay_type": "SALARIED",
            "annual_salary": "$90,000",
            "hourly_rate": "",
            "effective_from": "2026-10-01",
        },
    )
    assert response.status_code == 302
    latest = org.dev1.pay_records.order_by("pk").last()
    assert (latest.hourly_rate, latest.annual_salary) == (Decimal("43.27"), Decimal("90000.00"))
    assert latest.created_by == org.hr
    row = AuditLog.objects.get(entity_type="Pay", action="CREATE")
    assert (row.before["hourly_rate"], row.after["hourly_rate"]) == ("50.00", "43.27")
    bad = client.post(
        admin_url("pay", org.dev1.pk),
        {"pay_type": "HOURLY", "annual_salary": "1", "hourly_rate": "x", "effective_from": ""},
    )
    assert bad.status_code == 200 and org.dev1.pay_records.count() == 2
    assert "Type an amount" in bad.content.decode()
    change = client.get(admin_url("change", org.dev1.pk)).content.decode()
    assert 'id="pay-history"' in change and "Salaried: $43.27 an hour" in change
    listing = client.get(admin_url("changelist")).content.decode()
    assert "43.27" not in listing and 'id="pay-export-csv"' in listing
    export = client.get(admin_url("export")).content.decode("utf-8-sig")
    assert "salary" not in export and "hourly_rate" not in export and "43.27" not in export
    for person in (org.manager, org.payroll, org.dev1):
        assert login_as(person).get(admin_url("pay", org.dev1.pk)).status_code == 403
        assert login_as(person).get(admin_url("pay_export")).status_code == 403
    assert "43.27" not in login_as(org.dev1).get(reverse("profile")).content.decode()
    assert not hasattr(PayRecord, "admin_url")  # not registered: no list, add or delete pages
    assert login_as(org.hr).get("/admin/directory/payrecord/").status_code == 404


def upload(client, text, confirm=False):
    url = admin_url("pay_import")
    file = SimpleUploadedFile("pay.csv", text.encode(), content_type="text/csv")
    response = client.post(url, {"file": file})
    if confirm:
        return client.post(url, {"confirm": "1", "payload": response.context["payload"]})
    return response


def test_pay_csv(org, login_as, fixed_now):
    """T-260: the Pay CSV — export (every record, admins only, formula-safe, audited) and
    import (preview, errors with line numbers, all or nothing, unchanged rows, corrections,
    each added record audited) (D-167)."""
    pay(org.dev1, "50.00", start=date(2026, 1, 4), salary="104000")
    client = login_as(org.hr)
    exported = client.get(admin_url("pay_export"))
    assert exported["Content-Disposition"].startswith('attachment; filename="pay-')
    rows = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert rows == [
        ["employee_code", "pay_type", "annual_salary", "hourly_rate", "effective_from"],
        ["DEV1", "SALARIED", "104000.00", "50.00", "2026-01-04"],
    ]
    assert AuditLog.objects.get(action="EXPORT", entity_type="Pay").after == {"rows": 1}

    header = "employee_code,pay_type,annual_salary,hourly_rate,effective_from\n"
    lines = (
        "NOPE,HOURLY,,20,2026-10-01",
        "DEV2,HOURLY,5,20,2026-10-01",
        "DEV2,SALARIED,abc,,2026-10-01",
        "DEV2,HOURLY,,25,2019-01-01",
        "DEV2,HOURLY,,25,10/01/2026",
    )
    bad = upload(client, header + "\n".join(lines) + "\n")
    assert bad.context["errors"] == [
        "Line 2: unknown employee_code NOPE.",
        "Line 3: leave the annual salary empty for an hourly employee.",
        "Line 4: annual_salary is not an amount.",
        "Line 5: pay can't start before the hire date (2024-01-08).",
        "Line 6: effective_from must look like 2026-10-01.",
    ]
    assert PayRecord.objects.count() == 1

    twice = upload(client, header + "DEV2,HOURLY,,20,2026-10-01\nDEV2,HOURLY,,21,2026-10-01\n")
    assert twice.context["errors"] == ["Line 3: DEV2 already has a row for 2026-10-01 on line 2."]
    good = (
        header
        + "DEV1,SALARIED,104000,50.00,2026-01-04\n"  # identical to the record: unchanged
        + "dev2,HOURLY,,$31.25,2026-10-01\n"
        + 'MANAGER,SALARIED,"130,000",,2026-10-01\n'
    )
    result = upload(client, good).context["preview"]
    assert (result.added, result.corrections, result.unchanged) == (2, 0, 1)
    assert PayRecord.objects.count() == 1  # nothing changed by the preview
    assert upload(client, good, confirm=True).status_code == 302
    correction = header + "DEV1,SALARIED,104000,50.50,2026-01-04\n"  # same date, other rate
    result = upload(client, correction).context["preview"]
    assert (result.added, result.corrections) == (1, 1)
    assert result.changes == [("DEV1", date(2026, 1, 4), "correction")]
    upload(client, correction, confirm=True)
    assert PayRecord.objects.count() == 4
    manager = PayRecord.objects.get(employee=org.manager)
    assert (manager.hourly_rate, manager.created_by) == (Decimal("62.50"), org.hr)
    assert AuditLog.objects.filter(entity_type="Pay", action="CREATE").count() == 3
    assert login_as(org.manager).get(admin_url("pay_import")).status_code == 403

    PayRecord.objects.create(
        employee=org.dev2,
        pay_type="HOURLY",
        hourly_rate=Decimal("1"),
        effective_from=date(2026, 1, 4),
    )
    tricky = login_as(org.hr).get(admin_url("pay_export")).content.decode("utf-8-sig")
    assert "DEV2,HOURLY,,1.00,2026-01-04" in tricky


def test_project_budgets_in_admin(org, project, login_as):
    """T-261: a project's budget and "costs count from" date are set in Admin and audited with
    before/after as exact text; empty = No budget set (D-168)."""
    client = login_as(org.hr)
    url = reverse("admin:timesheets_project_change", args=[project.pk])
    page = client.get(url).content.decode()
    assert 'name="budget"' in page and 'name="costs_from"' in page
    data = {"name": project.name, "active": "on", "tasks": [t.pk for t in project.tasks.all()]}
    client.post(url, {**data, "budget": "2500.50", "costs_from": "2026-09-01"})
    project.refresh_from_db()
    assert (project.budget, project.costs_from) == (Decimal("2500.50"), date(2026, 9, 1))
    row = AuditLog.objects.get(entity_type="Project", action="UPDATE")
    assert row.before == {"budget": None, "costs_from": None}
    assert row.after == {"budget": "2500.50", "costs_from": "2026-09-01"}
    refused = client.post(url, {**data, "budget": "-5"})
    assert refused.status_code == 200 and Project.objects.get(pk=project.pk).budget == Decimal(
        "2500.50"
    )
    client.post(url, {**data, "budget": "", "costs_from": ""})
    assert Project.objects.get(pk=project.pk).budget is None
