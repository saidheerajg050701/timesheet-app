"""Change 12: Reports → Project budget — labour cost of approved project hours against each
project's budget (D-169–D-172). Built on the Project hours report, approved hours only."""

import csv
import io
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import connections
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from openpyxl import load_workbook

from analytics.services.project_costs import project_costs
from audit.models import AuditLog
from directory.models import Employee, PayRecord
from tests.analytics.integration import test_project_report as hours_tests
from tests.analytics.integration.test_project_report import (
    MON,
    NOW,
    PERIOD,
    TUE,
    Params,
    entry,
    report_for,
    sheet,
)
from tests.analytics.integration.test_team import build_large_company
from tests.directory.integration.test_pay import pay
from tests.factories import ProjectFactory
from timesheets.models import Timesheet

PAGE = "project_budget"
booked, mobile = hours_tests.booked, hours_tests.mobile  # the same small company (fixtures)
TUESDAY_RAISE = TUE  # DEV1's raise: from Tuesday Sep 29


@pytest.fixture
def priced(org, booked, project, mobile):
    """Pay for the `booked` company (approved, Sep 27 – Oct 10):
    DEV1  hourly $50, $60 from Tue → I-001 Mon 8 h × 50 + Tue 8 h × 60 + Wed 8 h × 60 = $1,360
    DEV2  salaried $104,000 → $50 → I-002 16 h = $800
    MANAGER salaried $124,800 → $60 → I-001 4 h = $240
    OLD   no pay record → I-001 8 h "Rate missing"
    OPS1  hourly $33.33 (outside the director's tree) → I-002 8 h = $266.64
    Budgets: I-001 $2,000 (cost $1,600: 80 % At risk), I-002 $1,000 (cost $1,066.64: Over)."""
    pay(org.dev1, "50.00")
    pay(org.dev1, "60.00", start=TUESDAY_RAISE)
    pay(org.dev2, "50.00", salary="104000")
    pay(org.manager, "60.00", salary="124800")
    pay(org.ops1, "33.33")
    project.budget, mobile.budget = Decimal("2000"), Decimal("1000")
    project.save()
    mobile.save()
    return booked


def costs_for(viewer, **params):
    return project_costs(viewer, Params(params), NOW)


def by_code(report):
    return {p.project.code: p for p in report.by_project}


def test_cost_rules(org, priced, project, login_as, fixed_now):
    """T-262: cost = hours × the rate in force on the work date, rounded to cents per entry;
    a raise changes only later entries; only project work is costed; totals are sums of the
    rounded rows; approved hours only (an hours parameter is ignored); the overtime note
    (D-169)."""
    report = costs_for(org.director)
    dev1 = next(p for p in report.people if p.employee.employee_code == "DEV1")
    assert dev1.cost == Decimal("1360.00")  # 8 h × 50 + 16 h × 60
    assert {r.detail.category for r in report.rows} == {"PROJECT"}  # no meeting, break, leave
    assert report.cost == sum(r.cost for r in report.rows if r.pay) == Decimal("2400.00")
    assert report.minutes == 3 * 480 + 2 * 480 + 240 + 480
    assert [r.rate for r in report.rows if r.detail.person is dev1] == [
        Decimal("50.00"), Decimal("60.00"), Decimal("60.00")
    ]  # fmt: skip
    s = sheet(org.dev2, PERIOD + timedelta(weeks=1), "SUBMITTED")
    entry(s, PERIOD + timedelta(days=8), project=project)
    assert costs_for(org.director, hours="all").minutes == report.minutes  # approved only
    page = login_as(org.director).get(reverse(PAGE), {"hours": "all"}).content.decode()
    assert "Overtime premium not included" in page and "Approved hours only" in page
    assert 'name="hours"' not in page  # no Hours filter on this page


def test_rate_missing(org, priced, login_as, fixed_now):
    """T-263: hours without a pay rate are never costed at $0: listed (person, hours, dates)
    for admins, payroll and the person's managers, with a warning and a note on the project
    (D-169)."""
    for viewer in (org.director, org.manager, org.hr, org.payroll):
        report = costs_for(viewer)
        assert [(m.person.employee.employee_code, m.minutes, m.dates) for m in report.missing] == [
            ("OLD", 480, [MON])
        ], viewer
        assert report.unpriced == 480
        old = next(p for p in report.people if p.employee.employee_code == "OLD")
        assert (old.cost, old.unpriced) == (Decimal("0.00"), 480)
    assert costs_for(org.ops_manager).missing == []  # not their person
    assert by_code(costs_for(org.hr))["I-001"].total_unpriced == 480
    html = login_as(org.manager).get(reverse(PAGE)).content.decode()
    assert "8.00 h have no pay rate — costs are incomplete" in html and 'id="rate-missing"' in html
    assert "8.00 h without a pay rate not included" in html


def test_budget(org, priced, project, settings, fixed_now):
    """T-264: remaining, % used and status (thresholds from settings), No budget set; the
    budget compares with the whole project's approved cost since "costs count from" —
    everyone's, whatever the period or the viewer's tree (D-169)."""
    hr = by_code(costs_for(org.hr))
    one, two = hr["I-001"], hr["I-002"]
    assert (one.total_cost, one.remaining, one.used, one.status) == (
        Decimal("1600.00"), Decimal("400.00"), Decimal("80.0"), "At risk"
    )  # fmt: skip
    assert (two.total_cost, two.remaining, two.used, two.status) == (
        Decimal("1066.64"), Decimal("-66.64"), Decimal("106.7"), "Over budget"
    )  # fmt: skip
    director = by_code(costs_for(org.director))
    assert director["I-002"].total_cost == Decimal("1066.64")  # OPS1 is outside the tree …
    assert director["I-002"].cost == Decimal("800.00")  # … but not in "this period" for them
    settings.BUDGET_AT_RISK_PERCENT, settings.BUDGET_OVER_PERCENT = 85, 105
    assert by_code(costs_for(org.hr))["I-001"].status == "On track"
    settings.BUDGET_AT_RISK_PERCENT, settings.BUDGET_OVER_PERCENT = 80, 100

    older = sheet(org.dev1, PERIOD - timedelta(weeks=2))  # Sep 13, approved: before the period
    entry(older, PERIOD - timedelta(days=13), project=project)  # Mon Sep 14, 8 h × $50
    assert by_code(costs_for(org.hr))["I-001"].total_cost == Decimal("2000.00")  # 100 %
    assert by_code(costs_for(org.hr, period="this"))["I-001"].total_cost == Decimal("2000.00")
    assert by_code(costs_for(org.hr))["I-001"].status == "At risk"  # 100 % is not over
    project.costs_from = TUE  # only from Tue Sep 29: DEV1 Tue + Wed at $60
    project.save()
    assert by_code(costs_for(org.hr))["I-001"].total_cost == Decimal("960.00")
    third = ProjectFactory(number=3, name="Data Warehouse")
    listed = by_code(costs_for(org.hr, project="I-003"))
    assert (listed["I-003"].status, listed["I-003"].remaining, listed["I-003"].used) == (
        "No budget set", None, None
    )  # fmt: skip
    third.budget = Decimal("0")
    third.save()
    assert by_code(costs_for(org.hr, project="I-003"))["I-003"].status == "On track"


def test_totals_add_up(org, priced, login_as, fixed_now):
    """T-265: by project, team, manager, task, pay type, pay period and employee all add up
    to the Detail; the page, the Excel and the CSV agree; the hours equal the Project hours
    report with Approved (D-169, D-171)."""
    for params in ({"group": "team"}, {"group": "manager"}):
        report = costs_for(org.director, **params)
        total, minutes = report.cost, report.minutes
        assert sum(p.cost for p in report.by_project) == total
        assert sum(line.cost for line in report.by_task) == total
        assert sum(line.cost for line in report.by_pay_type) == total
        assert sum(line.cost for line in report.by_pay_period) == total
        assert sum(p.cost for p in report.people) == total
        assert sum(line.minutes for line in report.by_pay_type) == minutes
        groups = report.by_team or report.by_manager
        assert sum(g.cost for g in groups) == total
    managers = costs_for(org.director, group="manager").by_manager
    assert [(g.label, g.cost, g.rollup_cost) for g in managers] == [
        ("Mark Lee", Decimal("0.00"), Decimal("2400.00")),
        ("Priya Shah", Decimal("2400.00"), Decimal("2400.00")),
    ]
    types = {line.label: (line.minutes, line.cost) for line in costs_for(org.director).by_pay_type}
    assert types == {
        "Hourly": (1440, Decimal("1360.00")),
        "Salaried": (1200, Decimal("1040.00")),
        "Rate missing": (480, Decimal("0.00")),
    }
    hours = report_for(org.director, hours="approved")
    assert costs_for(org.director).minutes == hours.project_total
    client = login_as(org.director)
    book = load_workbook(io.BytesIO(client.get(reverse("project_budget_xlsx")).content))
    cost_column = [r[8] for r in book["By employee"].iter_rows(min_row=2, values_only=True)]
    assert round(sum(cost_column), 2) == 2400  # Excel gives numbers back as floats
    rows = list(
        csv.DictReader(
            io.StringIO(client.get(reverse("project_budget_csv")).content.decode("utf-8-sig"))
        )
    )
    assert sum(Decimal(r["cost"]) for r in rows if r["cost"]) == Decimal("2400.00")
    assert sum(Decimal(r["hours"]) for r in rows) == Decimal(hours.project_total) / 60


def test_who_sees_costs(org, priced, login_as, fixed_now):
    """T-266: employees get 403 and no menu item; managers and directors see their own tree's
    per-person costs and are refused outside it; admins and payroll see everyone; nobody sees
    an annual salary here (D-170)."""
    dev1 = login_as(org.dev1)
    for name in (PAGE, "project_budget_xlsx", "project_budget_csv"):
        assert dev1.get(reverse(name)).status_code == 403
    assert "Project budget" not in dev1.get(reverse("home")).content.decode()
    codes = lambda r: {p.employee.employee_code for p in r.people}  # noqa: E731
    assert codes(costs_for(org.manager)) == {"MANAGER", "DEV1", "DEV2", "OLD"}
    assert codes(costs_for(org.director)) == {"MANAGER", "DEV1", "DEV2", "OLD"}
    assert "OPS1" in codes(costs_for(org.payroll)) and "OPS1" in codes(costs_for(org.hr))
    director = login_as(org.director)
    assert "Project budget" in director.get(reverse("home")).content.decode()
    outside = {"scope": "manager", "manager": "OPSMGR"}
    for name in (PAGE, "project_budget_xlsx", "project_budget_csv"):
        assert director.get(reverse(name), outside).status_code == 403
    html = director.get(reverse(PAGE)).content.decode()
    assert "John Kim" in html and "$60.00" in html and "$1,360.00" in html  # rate and cost
    assert "Lena Park" not in html
    for client in (director, login_as(org.payroll)):
        texts = [
            client.get(reverse(PAGE)).content.decode(),
            client.get(reverse("project_budget_csv")).content.decode(),
        ]
        book = load_workbook(io.BytesIO(client.get(reverse("project_budget_xlsx")).content))
        texts += [str(c) for ws in book for row in ws.iter_rows(values_only=True) for c in row]
        assert not [
            t for t in texts if "104000" in t or "104,000" in t or "124800" in t or "124,800" in t
        ]


def test_costs_downloads(org, priced, login_as, fixed_now):
    """T-267: two separate files — costs (Excel tabs by role, USD format, formula-safe, CSV
    Detail columns) and the hours report with Approved — with their names; one EXPORT audit
    row per costs download (D-171)."""
    org.dev1.first_name = "=SUM(1)"
    org.dev1.save()
    client = login_as(org.director)
    page = client.get(reverse(PAGE))
    response = client.get(reverse("project_budget_xlsx"))
    assert response["Content-Disposition"] == (
        'attachment; filename="project-costs_2026-09-27_to_2026-10-10.xlsx"'
    )
    book = load_workbook(io.BytesIO(response.content))
    assert book.sheetnames == [
        "Summary", "By project", "By team", "By manager", "By task", "By pay type",
        "By pay period", "By employee", "Detail", "Rate missing",
    ]  # fmt: skip
    by_project = book["By project"]
    assert by_project["A1"].font.bold and by_project.freeze_panes == "A2"
    assert by_project["D2"].number_format == '"$"#,##0.00'
    assert by_project["D2"].value == 1600  # I-001's total cost to date, as a number
    names = [r[1] for r in book["By employee"].iter_rows(min_row=2, values_only=True)]
    assert "'=SUM(1) Kim" in names
    summary = {r[0]: r[1] for r in book["Summary"].iter_rows(min_row=2, values_only=True)}
    assert summary["Hours"] == "Approved only" and summary["Labour cost"] == 2400
    csv_response = client.get(reverse("project_budget_csv"))
    assert (
        'filename="project-costs_2026-09-27_to_2026-10-10.csv"'
        in csv_response["Content-Disposition"]
    )
    rows = list(csv.reader(io.StringIO(csv_response.content.decode("utf-8-sig"))))
    assert rows[0] == [
        "date", "week_start", "employee_code", "employee_name", "team", "manager",
        "project_code", "project_name", "task_code", "task_name", "charge_code", "hours",
        "pay_type", "hourly_rate", "cost", "rate_missing",
    ]  # fmt: skip
    old = [r for r in rows if r[2] == "OLD"][0]
    assert old[12:] == ["Rate missing", "", "", "yes"]
    assert any(r[2] == "DEV1" and r[13:15] == ["60.00", "480.00"] for r in rows)
    exports = AuditLog.objects.filter(action="EXPORT", entity_type="ProjectCosts")
    assert [(e.actor, e.after["format"], e.after["rows"]) for e in exports.order_by("pk")] == [
        (org.director, "xlsx", 7),
        (org.director, "csv", 7),
    ]
    hours_link = page.context["hours_xlsx_url"]
    assert hours_link.startswith(reverse("project_hours_xlsx")) and "hours=approved" in hours_link
    assert client.get(hours_link)["Content-Disposition"].endswith(
        'filename="project-hours_2026-09-27_to_2026-10-10.xlsx"'
    )
    payroll = login_as(org.payroll).get(reverse(PAGE))
    assert payroll.context["hours_xlsx_url"] == ""  # payroll's hours report is their own


@pytest.mark.django_db(databases=["default", "payroll"])
def test_seed_pay_and_budgets(demo_password, fixed_now):
    """T-268: seed_demo gives everyone pay but one, salaried rate = salary ÷ 2,080, some hourly
    people, one raise; budgets show On track, At risk and Over budget; I-008 has none (D-172)."""
    from django.core.management import call_command

    call_command("seed_demo", stdout=io.StringIO())
    without = Employee.objects.filter(pay_records__isnull=True)
    assert without.count() == 1 and without.get().team.name == "Data"
    salaried = PayRecord.objects.filter(pay_type="SALARIED")
    assert all(
        p.hourly_rate == (p.annual_salary / 2080).quantize(Decimal("0.01")) for p in salaried
    )
    assert PayRecord.objects.filter(pay_type="HOURLY").count() >= 5
    raised = [e for e in Employee.objects.all() if e.pay_records.count() == 2]
    assert len(raised) == 1
    admin = Employee.objects.filter(is_admin=True, status="ACTIVE").first()
    statuses = {p.project.code: p.status for p in costs_for(admin, period="12w").by_project}
    assert statuses["I-002"] == "Over budget" and statuses["I-003"] == "At risk"
    assert statuses["I-001"] == "On track" and "I-008" not in statuses  # closed, no budget
    assert {"On track", "At risk", "Over budget"} <= set(statuses.values())
    assert (
        AuditLog.objects.filter(entity_type="Pay", system_actor="seed_demo").count()
        == PayRecord.objects.count()
    )


def test_cost_query_count_is_fixed(project, fixed_now):
    """T-269: the same number of database reads for 24, 125 or ~500 people and 2 or 53 weeks
    (D-169)."""
    ceo, director, manager, total = build_large_company(project)
    Timesheet.objects.update(status="APPROVED")  # money counts approved hours only
    PayRecord.objects.bulk_create(
        PayRecord(
            employee=e,
            pay_type="HOURLY",
            hourly_rate=Decimal("40"),
            effective_from=date(2024, 1, 8),
        )
        for e in Employee.objects.all()
    )
    project.budget = Decimal("100000")
    project.save()
    counts = {}
    ranges = {
        "2w": {"period": "12w"},
        "53w": {"period": "custom", "from": "2025-10-26", "to": "2026-10-24"},
    }
    for person in (ceo, director, manager):
        for name, params in ranges.items():
            with CaptureQueriesContext(connections["default"]) as queries:
                report = costs_for(person, **params)
            counts[(person.employee_code, name)] = len(queries)
            assert report.cost > 0
    assert len(set(counts.values())) == 1, counts
