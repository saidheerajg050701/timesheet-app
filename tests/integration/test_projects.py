"""Change 10b: project I-codes and the project search box (D-155–D-158). The app assigns each
new project the next I-code; the grid's "+ Add row" and ⋮ Change row search active projects,
with the week owner's recent projects first while the box is empty."""

import importlib
from datetime import date

import pytest
from django.apps import apps
from django.db import IntegrityError, transaction
from django.urls import reverse

from audit.models import AuditLog
from audit.services.log import record
from tests.factories import ProjectFactory, TimeEntryFactory, TimesheetFactory, task
from timesheets.models import Project, TimeEntry, Timesheet
from timesheets.services.calendar import week_start_for
from timesheets.services.changes import raise_request
from timesheets.services.projects import (
    assign_code,
    format_code,
    next_number,
    project_options,
    recent_projects,
    search_projects,
)
from timesheets.services.tasks import charge_code

WEEK = date(2026, 10, 18)  # the current, open week at fixed_now
LAST_WEEK = date(2026, 10, 11)
PERIOD = date(2026, 9, 27)  # weeks of Sep 27 + Oct 4, both past their deadline
migration = importlib.import_module("timesheets.migrations.0008_project_i_codes")


def url(model, view, *args):
    return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_{view}", args=args)


def codes(projects):
    return [p.code for p in projects]


def add(name, active=True):
    project = assign_code(Project(name=name, active=active))
    project.save()
    return project


def test_code_generation(db):
    """T-238: the first project is I-001, then the next number after the highest; a number is
    never reused (deactivating changes nothing); I-1000 follows I-999 and sorts after it; a
    duplicate number or code is refused (D-155)."""
    assert (format_code(7), format_code(42), format_code(1000)) == ("I-007", "I-042", "I-1000")
    assert next_number() == 1
    first, second = add("Customer Portal"), add("Mobile App")
    assert (first.code, first.number, second.code) == ("I-001", 1, "I-002")
    second.active = False
    second.save()
    assert add("Data Warehouse").code == "I-003"  # I-002 stays taken although inactive
    ProjectFactory(number=999, name="Big")
    assert add("Bigger").code == "I-1000"
    assert codes(Project.objects.all())[-2:] == ["I-999", "I-1000"]  # by number, not as text
    assert codes(search_projects(""))[-2:] == ["I-999", "I-1000"]
    for clash in ({"number": 1, "code": "I-5000"}, {"number": 5000, "code": "I-001"}):
        with pytest.raises(IntegrityError), transaction.atomic():
            Project.objects.create(name="Copy", **clash)


def test_admin_assigns_the_code(org, login_as):
    """T-239: HR adds a project without typing a code: the app assigns the next I-code, shown
    read-only after saving; a posted code or number is ignored; audited; admins only (D-155)."""
    ProjectFactory(number=4, name="Existing")
    client = login_as(org.hr)
    page = client.get(url(Project, "add")).content.decode()
    assert 'name="code"' not in page and 'name="number"' not in page
    assert "The I-code (I-001, I-002, …) is assigned when you save." in page
    data = {"code": "PRJ-777", "number": "77", "name": "Pilot", "active": "on"}
    response = client.post(url(Project, "add"), {**data, "_continue": "1"})
    pilot = Project.objects.get(name="Pilot")
    assert (pilot.code, pilot.number) == ("I-005", 5)
    page = client.get(response.url).content.decode()
    assert 'name="code"' not in page and "I-005" in page  # read-only after saving
    client.post(url(Project, "change", pilot.pk), {**data, "name": "Pilot 2"})
    pilot.refresh_from_db()
    assert (pilot.code, pilot.name, pilot.active) == ("I-005", "Pilot 2", True)
    rows = AuditLog.objects.filter(entity_type="Project").order_by("pk")
    assert [(r.action, r.entity_id) for r in rows][:1] == [("CREATE", "I-005")]
    assert rows[0].after == {
        "code": "I-005",
        "name": "Pilot",
        "active": True,
        "budget": None,
        "costs_from": None,
    }
    listing = client.get(url(Project, "changelist")).context["cl"].result_list
    assert codes(listing) == ["I-004", "I-005"]  # by number
    assert login_as(org.manager).post(url(Project, "add"), data).status_code == 403
    assert not Project.objects.filter(code="PRJ-777").exists()


def test_migration_renames_projects(db, capsys):
    """T-240: the data step of timesheets/0008: PRJ-001 → I-001 … (number kept); odd codes and
    a number already taken get the next free numbers in code order, each printed; time
    entries, allowed tasks and audit rows unchanged; charge codes I-001-DEV; reverse → PRJ
    codes (D-156)."""
    old = {}
    for n, code in enumerate(("PRJ-002", "PRJ-001", "PILOT", "prj-003", "PRJ-1", "PRJ-008")):
        old[code] = ProjectFactory(number=10_000 + n, code=code, tasks=[task("DEV")])
    entry = TimeEntryFactory(project=old["PRJ-001"], task=task("DEV"))
    audit = record("CREATE", "Project", "PRJ-001", system_actor="seed_demo", after={"x": 1})

    migration.to_i_codes(apps, None)
    renamed = {code: Project.objects.get(pk=p.pk).code for code, p in old.items()}
    assert renamed == {
        "PRJ-001": "I-001",
        "PRJ-002": "I-002",
        "PRJ-008": "I-008",
        "PILOT": "I-009",  # odd codes and a taken number: next free, in code order
        "PRJ-1": "I-010",
        "prj-003": "I-011",
    }
    assert {p.number for p in Project.objects.all()} == {1, 2, 8, 9, 10, 11}
    printed = capsys.readouterr().out
    assert "Project PRJ-001 → I-001" in printed and "Project PILOT → I-009" in printed
    entry = TimeEntry.objects.get(pk=entry.pk)
    assert entry.project.code == "I-001" and entry.project_id == old["PRJ-001"].pk
    assert [t.code for t in entry.project.tasks.all()] == ["DEV"]
    assert charge_code(entry.project, entry.task) == "I-001-DEV"
    assert AuditLog.objects.get(pk=audit.pk).entity_id == "PRJ-001"  # never rewritten
    assert AuditLog.objects.count() == 1

    migration.to_prj_codes(apps, None)  # undoing the migration
    assert codes(Project.objects.all()) == [
        "PRJ-001", "PRJ-002", "PRJ-008", "PRJ-009", "PRJ-010", "PRJ-011"
    ]  # fmt: skip
    assert all(op.reversible for op in migration.Migration.operations)


def test_project_search(org, login_as, fixed_now):
    """T-241: the search matches the I-code or name, partial and in any case; inactive projects
    never show; sorted by I-code (I-010 after I-009); "No matching project" (D-157)."""
    ProjectFactory(number=10, name="Portal Admin")
    ProjectFactory(number=1, name="Customer Portal")
    ProjectFactory(number=2, name="Mobile App")
    ProjectFactory(number=9, name="Data Warehouse")
    ProjectFactory(number=3, name="Old Portal", active=False)
    assert codes(search_projects("portal")) == ["I-001", "I-010"]
    assert codes(search_projects("  PORTAL ")) == ["I-001", "I-010"]
    assert codes(search_projects("i-00")) == ["I-001", "I-002", "I-009"]
    assert codes(search_projects("001")) == ["I-001"]
    assert codes(search_projects("I-010")) == ["I-010"]
    assert codes(search_projects("ware")) == ["I-009"]
    assert codes(search_projects("")) == ["I-001", "I-002", "I-009", "I-010"]
    assert search_projects("zzz") == [] and search_projects("old portal") == []

    client = login_as(org.dev1)
    found = client.get(reverse("timesheet_projects", args=[WEEK]), {"q": "portal"})
    html = found.content.decode()
    assert found.status_code == 200 and "Matching projects" in html
    assert html.index('data-label="I-001 Customer Portal"') < html.index("I-010 Portal Admin")
    assert 'role="option"' in html and "Old Portal" not in html
    empty = client.get(reverse("timesheet_projects", args=[WEEK]), {"q": "zzz"}).content.decode()
    assert "No matching project" in empty and 'role="option"' not in empty
    page = client.get(reverse("timesheet_week", args=[WEEK])).content.decode()
    projects_url = reverse("timesheet_projects", args=[WEEK])
    assert f'data-projects-url="{projects_url}"' in page and 'role="combobox"' in page


@pytest.mark.django_db(databases=["default", "payroll"])
def test_recent_projects(org, make_week, project, login_as, fixed_now):
    """T-242: with an empty box the week owner's active projects of the 4 weeks before the week
    come first, sorted by I-code, then the other active projects; Edit directly and the
    Approvals edit list the employee's projects, not the manager's; each list is refused to
    whoever can't use that editor (D-158)."""
    mobile = ProjectFactory(number=5, name="Mobile App")
    warehouse = ProjectFactory(number=3, name="Data Warehouse")
    too_old = ProjectFactory(number=4, name="Cloud Migration")
    closed = ProjectFactory(number=8, name="Legacy Billing")
    managers = ProjectFactory(number=7, name="Internal Operations")
    ProjectFactory(number=6, name="CRM Rollout")

    def book(employee, day, booked):
        start = week_start_for(day)
        sheet = Timesheet.objects.filter(employee=employee, week_start=start).first()
        sheet = sheet or TimesheetFactory(employee=employee, week_start=start)
        TimeEntryFactory(timesheet=sheet, work_date=day, project=booked)

    book(org.dev1, date(2026, 10, 12), mobile)  # last week
    book(org.dev1, date(2026, 9, 21), warehouse)  # 4 weeks back: Sep 20 – Sep 26
    book(org.dev1, date(2026, 9, 14), too_old)  # 5 weeks back
    book(org.dev1, date(2026, 10, 13), closed)
    book(org.dev1, date(2026, 10, 19), project)  # this week: not "before" it
    book(org.manager, date(2026, 10, 12), managers)
    closed.active = False
    closed.save()

    assert codes(recent_projects(org.dev1, WEEK)) == ["I-003", "I-005"]
    groups = project_options("", org.dev1, WEEK)
    assert [(heading, codes(projects)) for heading, projects in groups] == [
        ("Your recent projects", ["I-003", "I-005"]),
        ("All active projects", ["I-001", "I-004", "I-006", "I-007"]),
    ]
    assert [h for h, _ in project_options("mobile", org.dev1, WEEK)] == ["Matching projects"]
    html = login_as(org.dev1).get(reverse("timesheet_projects", args=[WEEK])).content.decode()
    assert html.index("Your recent projects") < html.index("I-003 Data Warehouse")
    assert html.index("I-005 Mobile App") < html.index("All active projects")

    change = raise_request(org.dev1, LAST_WEEK, "Monday is wrong", now=fixed_now)
    edit_list = reverse("request_projects", args=[change.pk])
    manager = login_as(org.manager)
    groups = manager.get(edit_list).context["groups"]
    assert groups[0][0] == "Your recent projects"
    assert codes(groups[0][1]) == ["I-003", "I-004"]  # DEV1's 4 weeks before Oct 11
    make_week(org.dev2, PERIOD)
    approval_list = reverse("approval_week_projects", args=[PERIOD, "DEV2", PERIOD])
    assert manager.get(approval_list).status_code == 200
    assert "Your recent projects" not in manager.get(approval_list).content.decode()

    assert login_as(org.dev2).get(edit_list).status_code == 403
    assert login_as(org.ops_manager).get(approval_list).status_code == 403
    dev1 = login_as(org.dev1)
    assert dev1.get(reverse("timesheet_projects", args=[LAST_WEEK])).status_code == 403  # locked
    assert dev1.post(reverse("timesheet_projects", args=[WEEK])).status_code == 405
