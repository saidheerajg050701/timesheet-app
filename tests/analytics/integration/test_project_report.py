"""Change 11: Reports → Project hours (D-160–D-164). One service gives the page, the Excel and
the CSV their numbers; who is in the report follows the Team rules (own hours for everyone,
the reporting tree for managers and directors, everyone for admins)."""

import csv
import io
from datetime import date, datetime, time, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command
from django.db import connections
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from openpyxl import load_workbook

from analytics.services.project_report import project_report
from analytics.services.report_files import MANAGING_TABS, OWN_TABS
from audit.models import AuditLog
from directory.models import Employee
from tests.analytics.integration.test_team import build_large_company
from tests.factories import (
    EmployeeFactory,
    ProjectFactory,
    TimeEntryFactory,
    TimesheetFactory,
    UserFactory,
    task,
)
from timesheets.models import TimeEntry

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)  # fixed_now
PERIOD = date(2026, 9, 27)  # the last pay period at fixed_now: Sep 27 – Oct 10
WEEK1, WEEK2 = PERIOD, PERIOD + timedelta(weeks=1)
MON, TUE, WED, THU, FRI, SAT = (WEEK1 + timedelta(days=n) for n in range(1, 7))
PAGE = "project_hours"


class Params(dict):
    """A QueryDict-like dict for calling the service directly."""

    def getlist(self, key):
        value = self.get(key, [])
        return value if isinstance(value, list) else [value]


def report_for(viewer, **params):
    return project_report(viewer, Params(params), NOW)


def codes(report):
    return [p.employee.employee_code for p in report.people]


def entry(sheet, day, category="PROJECT", project=None, task_code="DEV", minutes=480, **extra):
    start = extra.pop("start", time(9))
    timed = category in TimeEntry.TIMED  # leave has hours, no times
    end = (datetime.combine(day, start) + timedelta(minutes=minutes)).time() if timed else None
    return TimeEntryFactory(
        timesheet=sheet,
        work_date=day,
        category=category,
        project=project if category == "PROJECT" else None,
        task=task(task_code) if category == "PROJECT" and task_code else None,
        start_time=start if timed else None,
        end_time=end if timed else None,
        minutes=minutes,
        **extra,
    )


def sheet(employee, week=WEEK1, status="APPROVED"):
    return TimesheetFactory(employee=employee, week_start=week, status=status)


@pytest.fixture
def mobile(db):
    return ProjectFactory(number=2, name="Mobile App")


@pytest.fixture
def booked(org, project, mobile):
    """Approved hours in the last pay period (Sep 27 – Oct 10):
    DEV1  week 1: Mon DEV, Tue TST, Wed no task (I-001, 8 h each) + Thu Meetings 1 h,
          Fri Break 0.5 h; week 2: Mon PTO 8 h.
    DEV2  week 1: Mon, Tue on I-002 DEV.
    MANAGER week 1: Mon I-001 DEV 4 h + Training 2 h.
    OLD   (inactive, under MANAGER): week 1 Mon I-001 DEV 8 h.
    OPS1  (outside the director's tree): week 1 Mon I-002 DEV 8 h."""
    s = sheet(org.dev1)
    entry(s, MON, project=project)
    entry(s, TUE, project=project, task_code="TST")
    entry(s, WED, project=project, task_code=None)
    entry(s, THU, "MEETING", minutes=60, reason="Stand-up")
    entry(s, FRI, "BREAK", minutes=30, reason="Lunch")
    entry(sheet(org.dev1, WEEK2), WEEK2 + timedelta(days=1), "PTO", start=None, reason="Off")
    s = sheet(org.dev2)
    entry(s, MON, project=mobile)
    entry(s, TUE, project=mobile)
    s = sheet(org.manager)
    entry(s, MON, project=project, minutes=240)
    entry(s, TUE, "TRAINING", minutes=120)
    old = EmployeeFactory(
        employee_code="OLD", first_name="Olga", last_name="Old", manager=org.manager,
        status="INACTIVE", end_date=TUE,
    )  # fmt: skip
    entry(sheet(old), MON, project=project)
    entry(sheet(org.ops1), MON, project=mobile)
    return old


def test_employees_see_only_their_own_hours(org, booked, project, login_as, fixed_now):
    """T-244: an employee and a payroll-only user see and download only their own hours; any
    scope, manager or group parameter is refused (403) on the page and the downloads (D-160)."""
    dev1 = login_as(org.dev1)
    page = dev1.get(reverse(PAGE))
    report = page.context["report"]
    html = page.content.decode()
    assert report.own and codes(report) == ["DEV1"]
    assert report.project_total == 3 * 480 and report.non_project_total == 60
    assert 'href="/reports/project-hours/"' in html and ">Reports<" in html  # in the menu
    assert 'id="by-employee"' not in html and 'name="scope"' not in html
    for params in ({"scope": "tree"}, {"manager": "DEV2"}, {"group": "manager"}):
        for name in (PAGE, "project_hours_xlsx", "project_hours_csv"):
            assert dev1.get(reverse(name), params).status_code == 403, (name, params)
    rows = list(
        csv.DictReader(
            io.StringIO(dev1.get(reverse("project_hours_csv")).content.decode("utf-8-sig"))
        )
    )
    assert {r["employee_code"] for r in rows} == {"DEV1"}

    payroll = login_as(org.payroll)  # payroll staff who manage nobody: their own hours only
    entry(sheet(org.payroll), MON, project=project)
    report = payroll.get(reverse(PAGE)).context["report"]
    assert report.own and codes(report) == ["PAYROLL"] and report.project_total == 480
    assert payroll.get(reverse(PAGE), {"scope": "tree"}).status_code == 403
    workbook = load_workbook(io.BytesIO(payroll.get(reverse("project_hours_xlsx")).content))
    assert workbook.sheetnames == list(OWN_TABS)


def test_who_managers_directors_and_admins_see(org, booked, login_as, fixed_now):
    """T-245: a manager sees themselves and their tree; a director all their managers' groups;
    an admin everyone; one manager's group only inside the viewer's tree (else 403); direct
    reports only (D-160)."""
    assert codes(report_for(org.manager)) == ["DEV1", "DEV2", "OLD", "MANAGER"]  # hours first
    director = report_for(org.director)
    assert set(codes(director)) == {"DIRECTOR", "MANAGER", "DEV1", "DEV2", "OLD"}
    assert [(g.label, g.depth) for g in director.by_manager] == [("Mark Lee", 0), ("Priya Shah", 1)]
    assert [m.employee_code for m in director.manager_choices] == ["DIRECTOR", "MANAGER"]
    everyone = report_for(org.hr)
    assert set(codes(everyone)) == {e.employee_code for e in Employee.objects.all()}
    assert "OPS1" in codes(everyone) and "OPS1" not in codes(director)

    group = report_for(org.director, scope="manager", manager="MANAGER")
    assert set(codes(group)) == {"MANAGER", "DEV1", "DEV2", "OLD"}
    assert set(codes(report_for(org.director, scope="direct"))) == {"DIRECTOR", "MANAGER"}
    client = login_as(org.director)
    for params in (
        {"scope": "manager", "manager": "OPSMGR"},  # outside the tree
        {"scope": "manager", "manager": "NOBODY"},  # unknown
    ):
        for name in (PAGE, "project_hours_xlsx", "project_hours_csv"):
            assert client.get(reverse(name), params).status_code == 403, (name, params)
    up = {"scope": "manager", "manager": "DIRECTOR"}  # Priya is offered no People choice:
    fallback = login_as(org.manager).get(reverse(PAGE), up)  # … her whole tree (D-165)
    assert fallback.status_code == 200
    assert set(codes(fallback.context["report"])) == {"MANAGER", "DEV1", "DEV2", "OLD"}
    assert (
        login_as(org.hr).get(reverse(PAGE), {"scope": "manager", "manager": "OPSMGR"}).status_code
        == 200
    )


def test_numbers_add_up(org, booked, project, mobile, fixed_now):
    """T-246: by project = by task = project × task = by week = By employee project totals;
    By team and the managers' own groups add up to the totals; the roll-up includes the
    manager's own hours; non-project time apart; Break and leave never count; "Task not
    recorded"; an inactive employee with hours is included and marked (D-161, D-162)."""
    report = report_for(org.director, group="manager")
    project_hours = 3 * 480 + 2 * 480 + 240 + 480  # DEV1, DEV2, MANAGER, OLD
    assert report.project_total == project_hours
    assert sum(m for _, m, _ in report.by_project) == project_hours
    assert sum(m for _, _, m in report.by_task) == project_hours
    assert sum(report.matrix.values()) == project_hours
    assert sum(p for _, p, _ in report.by_week) == project_hours
    assert sum(p.project for p in report.people) == project_hours
    assert [(p.code, m, n) for p, m, n in report.by_project] == [
        ("I-001", 3 * 480 + 240 + 480, 3),
        ("I-002", 2 * 480, 1),
    ]
    assert dict((code or "none", m) for code, _, m in report.by_task)["none"] == 480
    assert report.by_task[-1][1] == "Task not recorded"
    assert report.non_project == [("Meetings", 60), ("Training", 120), ("Other", 0)]
    assert report.total == project_hours + 180  # Break (30 min) and PTO (8 h) never count
    dev1 = next(p for p in report.people if p.employee.employee_code == "DEV1")
    assert (dev1.project, dev1.non_project_total, dev1.leave, dev1.total) == (1440, 60, 480, 1500)
    assert sum(g.project for g in report.by_team) == project_hours
    assert sum(g.total for g in report.by_team) == report.total
    assert sum(g.project for g in report.by_manager) == project_hours
    assert sum(g.total for g in report.by_manager) == report.total
    top, mid = report.by_manager
    assert (top.employee, mid.employee) == (org.director, org.manager)
    assert mid.project == 3 * 480 + 2 * 480 + 240 + 480  # MANAGER + DEV1 + DEV2 + OLD
    assert top.rollup_project == top.project + mid.rollup_project  # the director's full picture
    old = next(p for p in report.people if p.employee.employee_code == "OLD")
    assert old.inactive and old.project == 480
    assert sum(r.minutes for r in report.detail) == report.total
    assert not [r for r in report.detail if r.category in ("BREAK", "PTO")]


def test_filters(org, project, mobile, login_as, fixed_now):
    """T-247: Hours (approved / + submitted / everything); periods are whole Sunday–Saturday
    weeks; custom dates widen to whole weeks; bad dates and more than 53 weeks fall back with a
    message; a project filter keeps non-project time; inactive projects can be chosen; unknown
    codes are left out with a message (D-161)."""
    entry(sheet(org.dev1, WEEK1, "APPROVED"), MON, project=project)
    entry(
        sheet(org.dev1, WEEK2, "SUBMITTED"), WEEK2 + timedelta(days=6), project=project
    )  # Sat Oct 10
    draft = sheet(org.dev1, WEEK2 + timedelta(weeks=1), "DRAFT")  # Oct 11: this pay period
    entry(draft, WEEK2 + timedelta(days=7), project=project)  # Sunday Oct 11
    entry(
        sheet(org.dev1, WEEK1 - timedelta(weeks=1), "APPROVED"),
        WEEK1 - timedelta(days=1),
        project=project,
    )  # Sat Sep 26
    assert report_for(org.dev1).project_total == 480
    assert report_for(org.dev1, hours="submitted").project_total == 960
    assert report_for(org.dev1, hours="all").project_total == 960  # Oct 11 is not in the period
    assert report_for(org.dev1, hours="all", period="this").project_total == 480
    four = report_for(org.dev1, period="4w", hours="all").filters
    assert (four.start, four.end) == (date(2026, 9, 27), date(2026, 10, 24))
    assert report_for(org.dev1, period="12w").filters.start == date(2026, 8, 2)
    custom = report_for(
        org.dev1, period="custom", hours="all", **{"from": "2026-09-30", "to": "2026-10-05"}
    )
    assert (custom.filters.start, custom.filters.end) == (WEEK1, date(2026, 10, 10))
    assert custom.project_total == 960 and [w for w, *_ in custom.by_week] == [WEEK1, WEEK2]
    wider = report_for(
        org.dev1, period="custom", hours="all", **{"from": "2026-09-26", "to": "2026-10-11"}
    )
    assert wider.project_total == 4 * 480  # Sep 20 – Oct 17: both boundary days now inside
    for bad in ({"from": "2026-10-10", "to": "2026-09-27"}, {"from": "x", "to": ""},
                {"from": "2025-01-01", "to": "2026-10-10"}):  # fmt: skip
        fallback = report_for(org.dev1, period="custom", **bad)
        assert fallback.filters.period == "last" and fallback.filters.messages, bad

    s = sheet(org.dev2)
    entry(s, MON, project=project)
    entry(s, TUE, project=mobile)
    entry(s, WED, "MEETING", minutes=60)
    mobile.active = False
    mobile.save()
    only = report_for(org.dev2, project="I-002")
    assert (only.project_total, only.non_project_total, only.total) == (480, 60, 540)
    assert [p.code for p, _, _ in only.by_project] == ["I-002"]
    both = report_for(org.dev2, project=["I-001", "I-002"])
    assert both.project_total == 960 and both.total == 1020
    unknown = report_for(org.dev2, project=["I-999", "I-001"])
    assert unknown.project_total == 480 and "Unknown project I-999" in unknown.filters.messages[0]
    listing = login_as(org.dev2).get(reverse("report_projects"), {"q": "mobile"}).content.decode()
    assert "I-002" in listing and "(inactive)" in listing


def test_by_employee_lists_everyone(org, project, mobile, fixed_now):
    """T-248: By employee lists everyone in scope employed in the period: people with project
    hours first, then 0.00 rows with a note; leave shown, never added; "X with hours of Y
    people"; "Show people with no hours" off hides the 0.00 rows (D-162)."""
    entry(sheet(org.dev1), MON, project=project)
    entry(sheet(org.dev2), MON, project=mobile)  # other project
    waiting = EmployeeFactory(employee_code="WAIT", last_name="Waiting", manager=org.manager)
    entry(sheet(waiting, status="SUBMITTED"), MON, project=project)  # not approved yet
    talker = EmployeeFactory(employee_code="TALK", last_name="Talker", manager=org.manager)
    entry(sheet(talker), MON, "MEETING", minutes=120)
    away = EmployeeFactory(employee_code="AWAY", last_name="Away", manager=org.manager)
    entry(sheet(away), MON, "PTO", start=None)
    EmployeeFactory(employee_code="LATE", manager=org.manager, hire_date=date(2026, 10, 12))
    report = report_for(org.manager, project="I-001")
    assert codes(report)[0] == "DEV1" and "LATE" not in codes(report)  # hired after the period
    notes = {p.employee.employee_code: p.note for p in report.people}
    assert notes == {
        "DEV1": "",
        "DEV2": "Worked on other projects",
        "WAIT": "Hours not approved yet",
        "TALK": "Only non-project time",
        "AWAY": "On leave",
        "MANAGER": "No time entered",
    }
    zero = [p for p in report.people if not p.has_hours]
    assert codes(report).index("DEV1") < min(
        codes(report).index(p.employee.employee_code) for p in zero
    )
    away_row = next(p for p in report.people if p.employee.employee_code == "AWAY")
    assert (away_row.leave, away_row.total) == (480, 0)
    assert (report.with_hours, len(report.people)) == (1, 6)
    assert report.total == 480 + 120  # TALK's meeting counts, AWAY's leave does not
    hidden = report_for(org.manager, project="I-001", empty="0")
    assert [p.employee.employee_code for p in hidden.shown_people] == ["DEV1"]
    assert len(hidden.people) == 6  # still counted: "1 with hours of 6 people"


def test_excel(org, booked, login_as, fixed_now):
    """T-249: the Excel has the tabs that fit the viewer, the same totals as the page, bold
    frozen headers, hours as numbers, formula-safe text and the agreed file names (D-163)."""
    org.dev1.first_name = '=HYPERLINK("x")'
    org.dev1.save()
    client = login_as(org.director)
    page = client.get(reverse(PAGE)).context["report"]
    response = client.get(reverse("project_hours_xlsx"))
    assert response["Content-Disposition"] == (
        'attachment; filename="project-hours_2026-09-27_to_2026-10-10.xlsx"'
    )
    book = load_workbook(io.BytesIO(response.content))
    assert book.sheetnames == list(MANAGING_TABS)
    summary = {row[0]: row[1] for row in book["Summary"].iter_rows(min_row=2, values_only=True)}
    assert summary["Project hours"] == round(page.project_total / 60, 2)
    assert summary["Total time"] == round(page.total / 60, 2)
    assert summary["People"] == "4 with hours of 5 people"
    by_project = book["By project"]
    assert by_project["A1"].font.bold and by_project.freeze_panes == "A2"
    total_row = [r for r in by_project.iter_rows(values_only=True) if r[0] == "Total"][0]
    assert total_row[2] == round(page.project_total / 60, 2)
    hours_cell = by_project["C2"]
    assert hours_cell.data_type == "n" and hours_cell.number_format == "0.00"
    names = [r[1] for r in book["By employee"].iter_rows(min_row=2, values_only=True)]
    assert '\'=HYPERLINK("x") Kim' in names
    detail = list(book["Detail"].iter_rows(min_row=2, values_only=True))
    assert round(sum(r[13] for r in detail), 2) == round(page.total / 60, 2)
    manager_rows = list(book["By manager"].iter_rows(min_row=2, values_only=True))
    assert round(sum(r[5] for r in manager_rows), 2) == round(page.total / 60, 2)

    own = login_as(org.dev1).get(reverse("project_hours_xlsx"))
    assert (
        'filename="project-hours_DEV1_2026-09-27_to_2026-10-10.xlsx"' in own["Content-Disposition"]
    )
    assert load_workbook(io.BytesIO(own.content)).sheetnames == list(OWN_TABS)


def test_csv_and_audit(org, booked, login_as, fixed_now):
    """T-250: the CSV Detail has one row per counted entry with the agreed columns, no reasons,
    formula-safe text and the agreed file name; its hours add up to the Total time; every
    download writes one EXPORT audit row and nothing else (D-163)."""
    org.dev2.first_name = "@evil"
    org.dev2.save()
    client = login_as(org.hr)
    entries_before = TimeEntry.objects.count()
    page = client.get(reverse(PAGE), {"project": "I-001"}).context["report"]
    response = client.get(reverse("project_hours_csv"), {"project": "I-001"})
    assert response["Content-Disposition"] == (
        'attachment; filename="project-hours_2026-09-27_to_2026-10-10.csv"'
    )
    text = response.content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == [
        "date", "week_start", "employee_code", "employee_name", "team", "department", "manager",
        "project_code", "project_name", "task_code", "task_name", "charge_code", "category",
        "hours", "week_status",
    ]  # fmt: skip
    assert round(sum(float(r[13]) for r in rows[1:]), 2) == round(page.total / 60, 2)
    assert "Stand-up" not in text and "Lunch" not in text and "reason" not in rows[0]
    assert ["2026-09-28", "2026-09-27", "DEV1", "John Kim"] == rows[1][:4]
    meeting = [r for r in rows if r[12] == "Meetings"][0]
    assert meeting[7:12] == ["", "", "", "", ""]  # non-project: no project or task
    assert any(r[11] == "I-001" and r[10] == "Task not recorded" for r in rows)
    assert any(r[11] == "I-001-TST" and r[13] == "8.00" and r[14] == "APPROVED" for r in rows)
    assert "DEV2" not in [r[2] for r in rows]  # DEV2 had no I-001 hours …
    client.get(reverse("project_hours_csv"))  # … all projects: DEV2's row is formula-safe
    client.get(reverse("project_hours_xlsx"), {"project": "I-001"})
    exports = AuditLog.objects.filter(action="EXPORT").order_by("pk")
    assert [(e.entity_type, e.entity_id, e.actor, e.after["format"]) for e in exports] == [
        ("ProjectReport", "2026-09-27..2026-10-10", org.hr, "csv"),
        ("ProjectReport", "2026-09-27..2026-10-10", org.hr, "csv"),
        ("ProjectReport", "2026-09-27..2026-10-10", org.hr, "xlsx"),
    ]
    assert exports[0].after["filters"]["project"] == ["I-001"]
    assert exports[0].after["rows"] == len(rows) - 1
    assert AuditLog.objects.exclude(action="EXPORT").count() == 0
    assert TimeEntry.objects.count() == entries_before
    everyone = client.get(reverse("project_hours_csv")).content.decode("utf-8-sig")
    assert ",'@evil Ng," in everyone


def test_query_count_is_fixed(project, fixed_now):
    """T-251: the same number of database reads for 24, 125 or ~500 people and for 2 or 53
    weeks; time_project_report writes nothing (D-164)."""
    ceo, director, manager, total = build_large_company(project)
    counts = {}
    ranges = {
        "2w": {"period": "last"},
        "53w": {"period": "custom", "from": "2025-10-26", "to": "2026-10-24"},
    }
    for person in (ceo, director, manager):
        for name, params in ranges.items():
            with CaptureQueriesContext(connections["default"]) as queries:
                report = report_for(person, hours="all", **params)
            counts[(person.employee_code, name)] = len(queries)
            assert report.people
    assert len(set(counts.values())) == 1, counts
    assert counts[("LCEO", "2w")] <= 8, counts
    big = report_for(ceo, hours="submitted", period="12w")
    assert len(big.people) == total and big.project_total > 0
    UserFactory(employee=ceo)
    out = StringIO()
    call_command("time_project_report", ceo.account.email, "--runs", "1", stdout=out)
    assert ", 0 writes" in out.getvalue() and f"{total} people" in out.getvalue()


def tabs(client, **params):
    return load_workbook(
        io.BytesIO(client.get(reverse("project_hours_xlsx"), params).content)
    ).sheetnames


SIMPLE_TABS = ["Summary", "By project", "By employee", "By task", "Project × task", "Detail"]


def test_a_manager_without_sub_managers_sees_no_extra_controls(org, project, login_as, fixed_now):
    """T-254: Priya manages nobody who manages, and her people are all in one team: no People
    and no Group by controls, no By team or By manager table or tab (D-165)."""
    entry(sheet(org.dev1), MON, project=project)
    client = login_as(org.manager)
    response = client.get(reverse(PAGE))
    report, html = response.context["report"], response.content.decode()
    assert (report.filters.scopes, report.filters.groups, report.filters.group) == ([], [], "")
    assert (
        'name="scope"' not in html and 'name="group"' not in html and 'name="manager"' not in html
    )
    assert 'id="by-manager"' not in html and 'id="by-team"' not in html
    assert 'id="by-employee"' in html and "Show people with no hours" in html
    assert [label for label, _ in response.context["described"]] == ["Period", "Projects", "Hours"]
    assert set(codes(report)) == {"MANAGER", "DEV1", "DEV2"}
    assert tabs(client) == SIMPLE_TABS


def test_two_teams_show_the_team_table(org, project, login_as, fixed_now):
    """T-255: with someone in another team under Priya, Team is the only grouping that
    changes anything: no Group by control, the By team table and tab, no By manager (D-165)."""
    other = EmployeeFactory(employee_code="NEW", last_name="Newer", manager=org.manager)
    entry(sheet(other), MON, project=project)
    client = login_as(org.manager)
    response = client.get(reverse(PAGE))
    report, html = response.context["report"], response.content.decode()
    assert (report.filters.groups, report.filters.group) == (["team"], "team")
    assert 'id="id_group"' not in html and 'name="group" value="team"' in html  # kept in links
    assert 'id="by-team"' in html and 'id="by-manager"' not in html
    other_team = f"{other.team.name} ({other.team.department})"
    assert sorted(g.label for g in report.by_team) == sorted([other_team, "Platform (Technology)"])
    assert tabs(client) == ["Summary", "By project", "By team", *SIMPLE_TABS[2:]]


def test_directors_and_admins_keep_every_option(org, booked, login_as, fixed_now):
    """T-256: Mark (a director) and HR see every People and Group by choice, both group tables
    in turn and every Excel tab, as before (D-165)."""
    for person in (org.director, org.hr):
        client = login_as(person)
        report = client.get(reverse(PAGE)).context["report"]
        assert report.filters.scopes == ["tree", "direct", "manager"]
        assert report.filters.groups == ["team", "manager"] and report.filters.group == "team"
        html = client.get(reverse(PAGE), {"group": "manager"}).content.decode()
        assert 'id="id_scope"' in html and 'id="id_group"' in html and 'id="by-manager"' in html
        assert html.count('<option value="manager"') == 2  # People and Group by
        assert tabs(client) == list(MANAGING_TABS)


def test_hidden_options_fall_back_safely(org, booked, project, login_as, fixed_now):
    """T-257: an address with an option that isn't offered still works: the default instead,
    no error and nobody extra — page and downloads alike; a director inside a manager's group
    sees only the groupings that change something there (D-165)."""
    client = login_as(org.manager)
    plain = client.get(reverse(PAGE)).context["report"]
    for params in (
        {"scope": "direct"},
        {"scope": "manager", "manager": "OPS1"},  # outside her tree: not an error, not shown
        {"scope": "manager", "manager": "NOBODY"},
        {"group": "manager"},
    ):
        response = client.get(reverse(PAGE), params)
        report = response.context["report"]
        assert response.status_code == 200, params
        assert codes(report) == codes(plain) and report.total == plain.total, params
        assert report.filters.scope == "tree" and report.filters.manager is None, params
        assert report.filters.group == plain.filters.group, params
        for name in ("project_hours_xlsx", "project_hours_csv"):
            assert client.get(reverse(name), params).status_code == 200, (name, params)
        assert tabs(client, **params) == tabs(client)
    assert (
        "OPS1"
        not in client.get(
            reverse("project_hours_csv"), {"scope": "manager", "manager": "OPS1"}
        ).content.decode()
    )
    drilled = login_as(org.director).get(
        reverse(PAGE), {"scope": "manager", "manager": "MANAGER", "group": "manager"}
    )
    report = drilled.context["report"]
    assert report.filters.groups == ["team"]  # OLD is in another team; By manager: one row
    assert 'id="by-manager"' not in drilled.content.decode() and report.filters.group == "team"
