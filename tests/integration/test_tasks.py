"""Change 10: project tasks and charge codes (D-148–D-154). Project work is booked to a task of
its project; the charge code "I-001-DEV" is worked out, never stored; payroll is unchanged."""

import importlib
import re
from datetime import date, datetime, time, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import pytest
from django.apps import apps
from django.contrib.messages import get_messages
from django.core.management import call_command
from django.urls import reverse

from analytics.services.metrics import dashboard_for
from audit.models import AuditLog
from payroll.models import PayrollWeek
from payroll.services.export import CSV_COLUMNS
from payroll.services.register import REGISTER_COLUMNS
from tests.factories import ProjectFactory, TimeEntryFactory, TimesheetFactory, task
from tests.forms import form, grid_post, work
from timesheets.models import Project, Task, TimeEntry, Timesheet
from timesheets.services.approvals import approve_period
from timesheets.services.changes import raise_request
from timesheets.services.validation import validate_entries

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)  # fixed_now
WEEK = date(2026, 10, 18)  # the current, open week
MONDAY, TUESDAY = WEEK + timedelta(days=1), WEEK + timedelta(days=2)
LAST_WEEK = date(2026, 10, 11)
PERIOD = date(2026, 9, 27)  # weeks of Sep 27 + Oct 4, both past their deadline
DEFAULT_CODES = ["PLN", "DES", "DEV", "TST", "REL", "SUP", "SEC", "DOC", "MTG"]
migration = importlib.import_module("timesheets.migrations.0007_default_tasks")


def url(model, view, *args):
    return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_{view}", args=args)


def audit(entity_type):
    rows = AuditLog.objects.filter(entity_type=entity_type).order_by("pk")
    return [(r.action, r.entity_id, r.before, r.after) for r in rows]


def notes(response):
    return [m.message for m in get_messages(response.wsgi_request)]


def week_url(week=WEEK):
    return reverse("timesheet_week", args=[week])


def deactivate(code):
    Task.objects.filter(code=code).update(active=False)


@pytest.fixture
def dev1(org, login_as, fixed_now):
    return login_as(org.dev1)


def test_task_admin(org, login_as):
    """T-227: Task admin — add, edit, deactivate with a note, code read-only, audited, never
    deleted, admins only (D-148)."""
    client = login_as(org.hr)
    data = {"code": "OPS", "name": "Operations", "description": "", "sort_order": "100"}
    assert client.post(url(Task, "add"), {**data, "active": "on"}).status_code == 302
    ops = Task.objects.get(code="OPS")
    page = client.get(url(Task, "change", ops.pk)).content.decode()
    assert 'name="code"' not in page and "0 saved entries (history keeps this task)" in page
    response = client.post(url(Task, "change", ops.pk), {**data, "code": "XXX", "name": "Ops"})
    ops.refresh_from_db()
    assert (ops.code, ops.name, ops.active) == ("OPS", "Ops", False)  # unticked = deactivated
    assert not [n for n in notes(response) if "is used by" in n]  # nothing uses OPS
    assert audit("Task") == [
        (
            "CREATE",
            "OPS",
            None,
            {
                "code": "OPS",
                "name": "Operations",
                "description": "",
                "active": True,
                "sort_order": 100,
            },
        ),
        ("UPDATE", "OPS", {"name": "Operations", "active": True}, {"name": "Ops", "active": False}),
    ]

    dev = task("DEV")
    TimeEntryFactory.create_batch(2, project=ProjectFactory(), task=dev)
    change = {"code": "DEV", "name": dev.name, "description": dev.description, "sort_order": "30"}
    response = client.post(url(Task, "change", dev.pk), change)  # deactivate a task in use
    assert response.status_code == 302 and not Task.objects.get(code="DEV").active
    assert (
        "DEV is used by 2 saved entries; open weeks must choose another task when they are "
        "saved again."
    ) in notes(response)
    assert TimeEntry.objects.filter(task=dev).count() == 2  # history keeps its task
    assert "2 saved entries" in client.get(url(Task, "change", dev.pk)).content.decode()

    assert client.get(url(Task, "delete", dev.pk)).status_code == 403
    assert client.post(url(Task, "delete", dev.pk), {"post": "yes"}).status_code == 403
    assert login_as(org.dev1).get(url(Task, "changelist")).status_code == 403
    assert login_as(org.manager).post(url(Task, "add"), data).status_code == 403
    assert Task.objects.filter(code="OPS").count() == 1


def test_allowed_tasks_per_project(org, login_as):
    """T-228: a new project starts with every active task ticked; changes to the list are
    audited; removing a task in use is allowed with a note; the data migration adds the 9
    defaults and links every existing project to them (D-148, D-149)."""
    deactivate("SEC")
    client = login_as(org.hr)
    initial = client.get(url(Project, "add")).context["adminform"].form.initial["tasks"]
    assert [t.code for t in initial] == [c for c in DEFAULT_CODES if c != "SEC"]
    page = client.get(url(Project, "add")).content.decode()
    assert "Allowed tasks" in page and 'type="checkbox" name="tasks"' in page

    dev, tst = task("DEV"), task("TST")
    data = {"name": "Pilot", "active": "on", "tasks": [dev.pk, tst.pk]}
    assert client.post(url(Project, "add"), data).status_code == 302
    pilot = Project.objects.get(code="I-001")
    assert {t.code for t in pilot.tasks.all()} == {"DEV", "TST"}
    TimeEntryFactory(project=pilot, task=tst)
    response = client.post(url(Project, "change", pilot.pk), {**data, "tasks": [dev.pk]})
    assert response.status_code == 302
    assert [t.code for t in pilot.tasks.all()] == ["DEV"]
    assert (
        "TST is used by 1 saved entry of I-001; open weeks must choose another task when they "
        "are saved again."
    ) in notes(response)
    assert TimeEntry.objects.get().task == tst  # history is never rewritten
    client.post(url(Project, "change", pilot.pk), {**data, "tasks": [dev.pk]})  # no change
    assert audit("Project") == [
        ("CREATE", "I-001", None, {"code": "I-001", "name": "Pilot", "active": True}),
        ("UPDATE", "I-001", {"tasks": []}, {"tasks": ["DEV", "TST"]}),
        ("UPDATE", "I-001", {"tasks": ["DEV", "TST"]}, {"tasks": ["DEV"]}),
    ]
    assert {r.actor for r in AuditLog.objects.filter(entity_type="Project")} == {org.hr}

    TimeEntry.objects.all().delete()  # the data migration on a database before Change 10
    Task.objects.all().delete()
    older = ProjectFactory(number=50, name="Old project", tasks=[])
    migration.add_default_tasks(apps, None)
    migration.add_default_tasks(apps, None)  # running it again changes nothing
    assert list(Task.objects.values_list("code", flat=True)) == DEFAULT_CODES
    assert list(Task.objects.values_list("sort_order", flat=True)) == list(range(10, 100, 10))
    assert str(Task.objects.get(code="MTG")) == "MTG Project Meetings & Coordination"
    assert Task.objects.get(code="REL").description == "Builds, deployments, production releases"
    assert [t.code for t in older.tasks.all()] == DEFAULT_CODES


def test_task_rules(dev1, project):
    """T-229: project work needs an active task its project allows; other categories have no
    task; an unknown code is refused; messages name entries by charge code (D-151)."""

    def problems(*rows):
        response = dev1.post(week_url(), form(*rows))
        assert response.status_code == 200 and not TimeEntry.objects.exists()
        return response.content.decode()

    assert "project work needs a task — choose one for I-001." in problems(
        work(MONDAY, "09:00", "12:00", project, task="")
    )
    assert "unknown task." in problems(work(MONDAY, "09:00", "12:00", project, task="ZZZ"))
    deactivate("SEC")
    assert "task SEC is no longer active." in problems(
        work(MONDAY, "09:00", "12:00", project, task="SEC")
    )
    project.tasks.remove(task("TST"))
    assert "task TST is not allowed for project I-001." in problems(
        work(MONDAY, "09:00", "12:00", project, task="TST")
    )
    meeting = {**work(MONDAY, "09:00", "10:00", category="MEETING"), "task": "DEV"}
    assert "only project work can have a task." in problems(meeting)
    project.tasks.add(task("TST"))
    html = problems(
        work(MONDAY, "09:00", "12:00", project), work(MONDAY, "11:00", "13:00", project, task="TST")
    )
    assert "09:00–12:00 I-001-DEV and 11:00–13:00 I-001-TST overlap." in html

    posted = form(
        work(MONDAY, "09:00", "12:00", project), work(MONDAY, "13:00", "15:00", project, task="TST")
    )
    assert dev1.post(week_url(), posted).status_code == 302
    saved = TimeEntry.objects.order_by("start_time")
    assert [(e.project.code, e.task.code) for e in saved] == [
        ("I-001", "DEV"),
        ("I-001", "TST"),
    ]
    with pytest.raises(Exception, match="task_only_for_project_work"):  # the database agrees
        TimeEntryFactory(category="MEETING", project=None, task=task("DEV"))


def test_grid_rows_per_project_and_task(dev1, project):
    """T-230: one grid row per project + task with its label and charge code; "+ Add row" takes
    only an allowed, active task; posted rows keep their task through a failed save (D-152)."""
    posted = form(
        work(MONDAY, "09:00", "12:00", project),
        work(MONDAY, "13:00", "15:00", project, task="TST"),
        work(TUESDAY, "09:00", "10:00", project, task="PLN"),
    )
    assert dev1.post(week_url(), posted).status_code == 302
    response = dev1.get(week_url())
    grid, html = response.context["grid"], response.content.decode()
    assert [r.key for r in grid.rows] == [
        f"PROJECT:{project.pk}:{c}" for c in ("PLN", "DEV", "TST")
    ]
    assert [(r.label, r.charge_code) for r in grid.rows] == [
        ("I-001 Customer Portal · PLN Planning & Analysis", "I-001-PLN"),
        ("I-001 Customer Portal · DEV Development", "I-001-DEV"),
        ("I-001 Customer Portal · TST Testing & QA", "I-001-TST"),
    ]
    assert 'title="Charge code">I-001-TST<' in html
    assert f'id="cell-project-{project.pk}-tst-{MONDAY.isoformat()}"' in html
    choices = response.context["task_choices"][str(project.pk)]
    assert choices[:3] == [["PLN", "PLN Planning & Analysis"], ["DES", "DES Design & Architecture"],
                           ["DEV", "DEV Development"]]  # fmt: skip
    assert 'id="task-choices"' in html and 'id="add-row-task"' in html

    row_url = reverse("timesheet_row", args=[WEEK])
    added = dev1.get(row_url, {"category": "PROJECT", "project": project.pk, "task": "SUP"})
    assert added.status_code == 200
    assert f'data-row-key="PROJECT:{project.pk}:SUP"' in added.content.decode()
    deactivate("SEC")
    project.tasks.remove(task("DOC"))
    for code, message in (
        ("", "Project work needs a task — choose one for I-001."),
        ("SEC", "Task SEC is no longer active."),
        ("DOC", "Task DOC is not allowed for project I-001."),
        ("ZZZ", "Project work needs a task — choose one for I-001."),
    ):
        refused = dev1.get(row_url, {"category": "PROJECT", "project": project.pk, "task": code})
        assert (refused.status_code, refused.content.decode()) == (400, message), code
    meeting = dev1.get(row_url, {"category": "MEETING", "project": project.pk, "task": "DEV"})
    assert 'data-row-key="MEETING:"' in meeting.content.decode()  # no project, no task

    failed = grid_post(grid)
    failed["grid-row"] = [*failed["grid-row"], f"PROJECT:{project.pk}:SUP"]
    failed.update({"entry-0-start": "9am"})
    response = dev1.post(week_url(), failed)
    keys = [r.key for r in response.context["grid"].rows]
    assert keys == [f"PROJECT:{project.pk}:{c}" for c in ("PLN", "DEV", "TST", "SUP")]


def test_row_menu_changes_the_task_in_every_editor(org, project, login_as, fixed_now):
    """T-231: ⋮ Change row sets another task (slots, times and reasons kept), merges into an
    existing project + task row, deletes; the same in Edit directly and the Approvals edit."""
    dev1 = login_as(org.dev1)
    rows_url = reverse("timesheet_rows", args=[WEEK])
    posted = form(
        work(MONDAY, "09:00", "12:00", project, reason="Login"),
        work(TUESDAY, "09:00", "11:00", project, task="TST", reason="Tests"),
    )

    def act(client, data, action, row, target_url, **target):
        data = {**data, "row-action": action, "row-key": row}
        data.update({f"new-{name}": value for name, value in target.items()})
        return client.post(target_url, data)

    dev, tst = f"PROJECT:{project.pk}:DEV", f"PROJECT:{project.pk}:TST"
    moved = act(dev1, posted, "change", dev, rows_url, category="PROJECT", project=project.pk,
                task="DES")  # fmt: skip
    grid = moved.context["grid"]
    assert [r.label for r in grid.rows] == [
        "I-001 Customer Portal · DES Design & Architecture",
        "I-001 Customer Portal · TST Testing & QA",
    ]
    assert "Moved 1 time slot to I-001 Customer Portal · DES Design &amp; Architecture." in (
        moved.content.decode()
    )
    merged = act(dev1, grid_post(grid), "change", tst, rows_url, category="PROJECT",
                 project=project.pk, task="DES").context["grid"]  # fmt: skip
    assert [(r.key, len([s for c in r.cells for s in c.slots])) for r in merged.rows] == [
        (f"PROJECT:{project.pk}:DES", 2)
    ]
    project.tasks.remove(task("REL"))
    refused = act(dev1, grid_post(merged), "change", f"PROJECT:{project.pk}:DES", rows_url,
                  category="PROJECT", project=project.pk, task="REL")  # fmt: skip
    assert refused.status_code == 400
    assert dev1.post(week_url(), grid_post(merged)).status_code == 302
    saved = TimeEntry.objects.order_by("work_date")
    assert [(e.task.code, e.start_time, e.reason) for e in saved] == [
        ("DES", time(9), "Login"),
        ("DES", time(9), "Tests"),
    ]
    deleted = act(dev1, grid_post(merged), "delete", f"PROJECT:{project.pk}:DES", rows_url)
    assert deleted.context["grid"].rows == []

    sheet = TimesheetFactory(employee=org.dev1, week_start=LAST_WEEK, status="SUBMITTED")
    TimeEntryFactory(timesheet=sheet, work_date=LAST_WEEK + timedelta(days=1), project=project)
    change = raise_request(org.dev1, LAST_WEEK, "That was testing", now=fixed_now)
    manager = login_as(org.manager)
    edit = reverse("request_edit", args=[change.pk])
    grid = manager.get(edit).context["grid"]
    grid = act(manager, grid_post(grid), "change", dev, reverse("request_rows", args=[change.pk]),
               category="PROJECT", project=project.pk, task="TST").context["grid"]  # fmt: skip
    assert (
        manager.post(edit, {**grid_post(grid), "note": "Testing, not development"}).status_code
        == 302
    )
    (row,) = AuditLog.objects.filter(action="UPDATE", entity_type="Timesheet")
    assert [e["task"] for e in row.before["entries"]] == ["DEV"]
    assert [e["task"] for e in row.after["entries"]] == ["TST"]

    locked = TimesheetFactory(employee=org.dev2, week_start=PERIOD, status="DRAFT")
    TimeEntryFactory(timesheet=locked, work_date=PERIOD + timedelta(days=1), project=project)
    args = [PERIOD, "DEV2", PERIOD]
    edit = reverse("approval_week_edit", args=args)
    grid = manager.get(edit).context["grid"]
    grid = act(manager, grid_post(grid), "change", dev, reverse("approval_week_rows", args=args),
               category="PROJECT", project=project.pk, task="PLN").context["grid"]  # fmt: skip
    assert [r.label for r in grid.rows] == ["I-001 Customer Portal · PLN Planning & Analysis"]
    assert manager.post(edit, {**grid_post(grid), "note": "Planning"}).status_code == 302
    assert TimeEntry.objects.get(timesheet__employee=org.dev2).task.code == "PLN"


def test_history_without_a_task(org, project, login_as, fixed_now):
    """T-232: entries saved before tasks show "Task not recorded" and stay as they are; saving
    that week again needs a task; after choosing one (⋮) it saves (D-151)."""
    old = TimesheetFactory(employee=org.dev1, week_start=PERIOD, status="SUBMITTED")
    TimeEntryFactory(timesheet=old, work_date=PERIOD + timedelta(days=1), project=project,
                     task=None)  # fmt: skip
    sheet = TimesheetFactory(employee=org.dev1, week_start=WEEK, status="DRAFT")
    TimeEntryFactory(timesheet=sheet, work_date=MONDAY, project=project, task=None)
    dev1 = login_as(org.dev1)

    label = "I-001 Customer Portal · Task not recorded"
    read_only = dev1.get(week_url(PERIOD))
    assert [r.label for r in read_only.context["grid"].rows] == [label]
    assert 'grid-label-sub is-unrecorded">· Task not recorded<' in read_only.content.decode()
    page = dev1.get(week_url())
    grid = page.context["grid"]
    assert [(r.key, r.label, r.charge_code) for r in grid.rows] == [
        (f"PROJECT:{project.pk}", label, "I-001")
    ]
    refused = dev1.post(week_url(), grid_post(grid))
    assert refused.status_code == 200
    assert "project work needs a task — choose one for I-001." in refused.content.decode()
    assert TimeEntry.objects.filter(task__isnull=True).count() == 2  # nothing rewritten
    approvals = login_as(org.manager).get(reverse("approval_detail", args=[PERIOD, "DEV1"]))
    assert label in approvals.content.decode()
    dev1 = login_as(org.dev1)

    fixed = dev1.post(
        reverse("timesheet_rows", args=[WEEK]),
        {**grid_post(grid), "row-action": "change", "row-key": f"PROJECT:{project.pk}",
         "new-category": "PROJECT", "new-project": project.pk, "new-task": "DEV"},
    ).context["grid"]  # fmt: skip
    assert dev1.post(week_url(), grid_post(fixed)).status_code == 302
    assert TimeEntry.objects.get(timesheet=sheet).task.code == "DEV"
    assert TimeEntry.objects.get(timesheet=old).task is None  # the submitted week is untouched


@pytest.fixture
def booked(org, make_week, project):
    """DEV1: last week 3 days DEV + 2 days TST (40 h); the week before without tasks (40 h)."""
    week = make_week(org.dev1, LAST_WEEK)
    for entry in week.entries.order_by("work_date")[3:]:
        entry.task = task("TST")
        entry.save()
    history = make_week(org.dev1, LAST_WEEK - timedelta(weeks=1))
    history.entries.update(task=None)
    mobile = ProjectFactory(number=2, name="Mobile App")
    make_week(org.dev2, LAST_WEEK, days=1).entries.update(project=mobile)  # 8 h I-002-DEV
    return mobile


def test_analytics_by_task_and_charge_code(org, booked, login_as, fixed_now):
    """T-233: dashboard and Team show hours by task and by project + task, "Task not recorded"
    as its own line; the project and category totals are unchanged (D-153)."""
    dash = dashboard_for(org.dev1, 12, NOW)
    assert dash.tasks == [
        ("DEV", "Development", 1440),
        ("TST", "Testing & QA", 960),
        ("", "Task not recorded", 2400),
    ]
    assert dash.charge_codes == [
        ("I-001-DEV", "Customer Portal", "Development", 1440),
        ("I-001-TST", "Customer Portal", "Testing & QA", 960),
        ("I-001", "Customer Portal", "Task not recorded", 2400),
    ]
    assert dash.projects == [("I-001", "Customer Portal", 4800)]
    assert dash.categories.total == 4800
    assert dash.chart_data["tasks"] == [
        {"label": "DEV", "hours": 24.0, "unrecorded": False},
        {"label": "TST", "hours": 16.0, "unrecorded": False},
        {"label": "Task not recorded", "hours": 40.0, "unrecorded": True},
    ]
    html = login_as(org.dev1).get(reverse("home")).content.decode()
    assert 'id="by-task"' in html and 'id="tasks-chart"' in html
    assert (
        'id="charge-codes-table"' in html and '<span class="grid-code">I-001-TST</span>' in html
    )

    response = login_as(org.manager).get(reverse("team"))
    board, html = response.context["board"], response.content.decode()
    assert board.tasks == [
        ("DEV", "Development", 1920),
        ("TST", "Testing & QA", 960),
        ("", "Task not recorded", 2400),
    ]
    assert [(code, m) for code, _, _, m in board.charge_codes] == [
        ("I-001-DEV", 1440),
        ("I-001-TST", 960),
        ("I-001", 2400),
        ("I-002-DEV", 480),
    ]
    assert sum(m for *_, m in board.projects) == sum(m for *_, m in board.tasks) == 5280
    assert board.chart_data["tasks"][-1]["label"] == "Task not recorded"
    assert 'id="team-by-task"' in html and "Hours by project + task across the team" in html


@pytest.mark.django_db(databases=["default", "payroll"])
def test_payroll_is_unchanged_by_tasks(org, make_week, project, django_capture_on_commit_callbacks):
    """T-234: payroll records and CSVs carry no project or task; totals equal the hours
    whatever the tasks (D-153)."""
    names = [name for name, _, _ in CSV_COLUMNS] + [name for name, *_ in REGISTER_COLUMNS]
    assert not [n for n in names if "task" in n or "project" in n or "charge" in n]
    first = make_week(org.dev1, PERIOD)
    for entry, code in zip(first.entries.order_by("work_date"), ["DEV", "TST", "PLN", "SUP", "MTG"],
                           strict=True):  # fmt: skip
        entry.task = task(code)
        entry.save()
    make_week(org.dev1, PERIOD + timedelta(weeks=1)).entries.update(task=None)  # history
    with django_capture_on_commit_callbacks(execute=True):
        approve_period(org.manager, org.dev1, PERIOD, now=NOW)
    weeks = PayrollWeek.objects.order_by("week_start")
    assert [(w.regular_minutes, w.overtime_minutes, w.total_minutes) for w in weeks] == [
        (2400, 0, 2400),
        (2400, 0, 2400),
    ]
    fields = {f.name for f in PayrollWeek._meta.get_fields()}
    assert not {f for f in fields if "task" in f or "project" in f}


@pytest.mark.django_db(databases=["default", "payroll"])
def test_seed_books_allowed_tasks(demo_password, fixed_now):
    """T-235: seed_demo gives each project its tasks and books every project entry to a task
    the project allows; every week still passes the entry rules (D-154, T-80)."""
    call_command("seed_demo", stdout=StringIO())
    assert list(Task.objects.values_list("code", flat=True)) == DEFAULT_CODES
    allowed = {p.code: {t.code for t in p.tasks.all()} for p in Project.objects.all()}
    assert allowed["I-005"] == {"SUP", "DOC", "TST", "MTG"}
    assert all(allowed.values())
    work = TimeEntry.objects.filter(category="PROJECT").select_related("project", "task")
    assert work.exists() and not work.filter(task__isnull=True).exists()
    assert all(e.task.code in allowed[e.project.code] for e in work)
    assert not TimeEntry.objects.exclude(category="PROJECT").filter(task__isnull=False).exists()
    assert len({e.task.code for e in work}) >= 6  # realistic variety, not one task for all
    platform = work.filter(timesheet__employee__team__name="Platform")
    assert {e.task.code for e in platform} <= {"DEV", "TST", "REL", "MTG", "PLN", "DES", "SUP"}
    for sheet in Timesheet.objects.select_related("employee")[:200]:
        entries = list(sheet.entries.all())
        assert validate_entries(sheet.employee, sheet.week_start, entries) == [], sheet
    snapshot = AuditLog.objects.get(entity_type="Project", entity_id="I-005", action="CREATE")
    assert snapshot.after["tasks"] == ["SUP", "DOC", "TST", "MTG"]
    assert re.fullmatch(r"I-\d{3}-[A-Z]{3}", f"{work[0].project.code}-{work[0].task.code}")


@pytest.mark.django_db(databases=["default", "payroll"])
def test_approve_after_a_task_is_removed(
    org, make_week, project, login_as, fixed_now, django_capture_on_commit_callbacks
):
    """T-237: a task deactivated or removed from the project after the weeks were SUBMITTED or
    LOCKED: the manager still approves them as they are (approval never re-checks tasks) and
    payroll gets the hours; only saving the week again asks for another task (D-149, D-151)."""
    week1, week2 = PERIOD, PERIOD + timedelta(weeks=1)
    make_week(org.dev1, week1).entries.update(task=task("SEC"))  # SUBMITTED
    make_week(org.dev1, week2, "DRAFT").entries.update(task=task("TST"))  # LOCKED, never submitted
    deactivate("SEC")
    project.tasks.remove(task("TST"))
    manager = login_as(org.manager)

    edit = reverse("approval_week_edit", args=[PERIOD, "DEV1", week1])
    resaved = manager.post(edit, grid_post(manager.get(edit).context["grid"]))
    assert resaved.status_code == 200 and "task SEC is no longer active." in (
        resaved.content.decode()
    )  # saving again re-checks the task; nothing saved
    detail = reverse("approval_detail", args=[PERIOD, "DEV1"])
    page = manager.get(detail).content.decode()
    assert "I-001-SEC" in page and "I-001-TST" in page
    with django_capture_on_commit_callbacks(execute=True):
        response = manager.post(detail, {"action": "approve", "confirm_unsubmitted": "1"})
    assert response.status_code == 302
    sheets = Timesheet.objects.filter(employee=org.dev1).order_by("week_start")
    assert [s.status for s in sheets] == ["APPROVED", "APPROVED"]
    assert sorted({e.task.code for e in TimeEntry.objects.all()}) == ["SEC", "TST"]  # as they were
    weeks = PayrollWeek.objects.filter(employee_code="DEV1").order_by("week_start")
    assert [w.total_minutes for w in weeks] == [2400, 2400]
