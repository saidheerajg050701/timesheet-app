"""Change 7: change or delete a whole grid row (D-129, D-130). The server re-draws the week as
typed; nothing is saved until the week itself is saved."""

import re
from datetime import date, time, timedelta

import pytest
from django.urls import reverse

from audit.models import AuditLog
from tests.factories import ProjectFactory, TimeEntryFactory, TimesheetFactory
from tests.forms import brk, form, grid_post, leave, work
from timesheets.models import ChangeRequest, TimeEntry, Timesheet
from timesheets.services.changes import raise_request, reject_request

WEEK = date(2026, 10, 18)  # the current week at fixed_now (Wed 21 Oct)
MONDAY, TUESDAY, WEDNESDAY = (WEEK + timedelta(days=n) for n in (1, 2, 3))
LAST_WEEK = date(2026, 10, 11)  # past its deadline (Sat 17 Oct 12:00)
OLDER_WEEK = date(2026, 10, 4)


@pytest.fixture
def dev1(org, login_as, fixed_now):
    return login_as(org.dev1)


@pytest.fixture
def mobile(db):
    return ProjectFactory(code="PRJ-002", name="Mobile App")


def week_url(week=WEEK):
    return reverse("timesheet_week", args=[week])


def rows_url(week=WEEK):
    return reverse("timesheet_rows", args=[week])


def key(category, project=None):
    return f"{category}:{project.pk if project else ''}"


def act(client, posted, action, row, url=None, **target):
    """POST the week as typed plus one row action, as grid.js does."""
    data = {**posted, "row-action": action, "row-key": row}
    data.update({f"new-{name}": value for name, value in target.items()})
    return client.post(url or rows_url(), data)


def slots_of(grid):
    """(index, day, category, project, start, end, reason) of every slot, in index order."""
    return sorted(
        (s.index, s.work_date, s.category, s.project, s.start, s.end, s.reason)
        for row in grid.rows
        for cell in row.cells
        for s in cell.slots
    )


def notice(html):
    return re.search(r'data-role="grid-notice" role="status" data-notice="([^"]*)"', html)[1]


def test_delete_a_row_with_slots(dev1, project):
    """T-191: Delete row removes the row's 3 slots (6.50 h) from the typed week; totals follow."""
    posted = form(
        work(MONDAY, "09:00", "12:00", project, reason="Login"),
        work(TUESDAY, "09:00", "11:30", project),
        work(WEDNESDAY, "13:00", "14:00", project),
        work(MONDAY, "13:00", "14:00", category="MEETING", reason="Stand-up"),
    )
    posted["grid-row"] = [key("PROJECT", project), "MEETING:"]
    response = act(dev1, posted, "delete", key("PROJECT", project))
    assert response.status_code == 200
    html = response.content.decode()
    grid = response.context["grid"]
    assert [r.label for r in grid.rows] == ["Meetings"]
    assert [m for _, m, _ in grid.footer] == [0, 60, 0, 0, 0, 0, 0] and grid.worked == 60
    assert 'data-role="week-total">1.00<' in html and 'data-role="row-total">1.00<' in html
    assert notice(html) == (
        "Deleted PRJ-001 Customer Portal / Project work (3 time slots). Save to keep this change."
    )
    assert not TimeEntry.objects.exists()  # nothing saved by the row action itself

    assert dev1.post(week_url(), grid_post(grid)).status_code == 302
    assert list(TimeEntry.objects.values_list("category", "reason")) == [("MEETING", "Stand-up")]


def test_delete_an_empty_row_and_a_break_row(dev1, project):
    """T-192: an empty row just disappears; deleting Break leaves Total worked hours unchanged."""
    posted = form(work(MONDAY, "09:00", "12:00", project), brk(MONDAY, "12:00", "12:30"))
    posted["grid-row"] = [key("PROJECT", project), "BREAK:", "TRAINING:"]
    response = act(dev1, posted, "delete", "TRAINING:")
    grid = response.context["grid"]
    assert [r.category for r in grid.rows] == ["PROJECT", "BREAK"]
    assert notice(response.content.decode()) == "Deleted Training."

    response = act(dev1, grid_post(grid), "delete", "BREAK:")
    grid = response.context["grid"]
    assert [r.category for r in grid.rows] == ["PROJECT"] and grid.worked == 180
    assert dev1.post(week_url(), grid_post(grid)).status_code == 302
    html = dev1.get(week_url()).content.decode()
    assert 'id="week-break">0:00<' in html and 'id="week-worked">3:00<' in html
    assert not TimeEntry.objects.filter(category="BREAK").exists()


def test_change_project(dev1, project, mobile):
    """T-193: PRJ-001 → PRJ-002 keeps every slot's day, times and reason; saved as PRJ-002."""
    posted = form(
        work(MONDAY, "09:00", "12:00", project, reason="Login"),
        work(TUESDAY, "13:00", "15:00", project, reason=""),
    )
    response = act(
        dev1, posted, "change", key("PROJECT", project), category="PROJECT", project=mobile.pk
    )
    grid = response.context["grid"]
    assert [r.label for r in grid.rows] == ["PRJ-002 Mobile App / Project work"]
    assert slots_of(grid) == [
        (0, MONDAY.isoformat(), "PROJECT", str(mobile.pk), "09:00", "12:00", "Login"),
        (1, TUESDAY.isoformat(), "PROJECT", str(mobile.pk), "13:00", "15:00", ""),
    ]
    assert grid.worked == 300
    assert notice(response.content.decode()) == (
        "Moved 2 time slots to PRJ-002 Mobile App / Project work. Save to keep this change."
    )
    assert not TimeEntry.objects.exists()
    assert dev1.post(week_url(), grid_post(grid)).status_code == 302
    saved = TimeEntry.objects.order_by("work_date")
    assert [(e.project.code, e.start_time, e.end_time, e.reason) for e in saved] == [
        ("PRJ-002", time(9), time(12), "Login"),
        ("PRJ-002", time(13), time(15), ""),
    ]


def test_change_into_an_existing_row_merges(dev1, project, mobile):
    """T-194: the target row already exists → slots merge into it; overlaps still refused."""
    posted = form(work(MONDAY, "09:00", "12:00", project), work(MONDAY, "13:00", "17:00", mobile))
    response = act(
        dev1, posted, "change", key("PROJECT", project), category="PROJECT", project=mobile.pk
    )
    grid = response.context["grid"]
    assert [r.label for r in grid.rows] == ["PRJ-002 Mobile App / Project work"]
    assert len(grid.rows[0].cells[1].slots) == 2 and grid.worked == 420
    assert notice(response.content.decode()) == (
        "Moved 1 time slot to PRJ-002 Mobile App / Project work, merged with its existing row. "
        "Save to keep this change."
    )
    assert dev1.post(week_url(), grid_post(grid)).status_code == 302
    assert set(TimeEntry.objects.values_list("project__code", flat=True)) == {"PRJ-002"}

    clashing = form(work(MONDAY, "09:00", "12:00", project), work(MONDAY, "11:00", "13:00", mobile))
    grid = act(
        dev1, clashing, "change", key("PROJECT", project), category="PROJECT", project=mobile.pk
    ).context["grid"]
    html = dev1.post(week_url(), grid_post(grid)).content.decode()
    message = "Mon 19 Oct: 09:00–12:00 PRJ-002 and 11:00–13:00 PRJ-002 overlap."
    target = f"cell-project-{mobile.pk}-{MONDAY.isoformat()}"
    assert message in html and re.search(rf'aria-controls="{target}"[^>]*aria-invalid="true"', html)
    assert TimeEntry.objects.filter(start_time=time(13)).count() == 1  # the earlier save, kept


def test_allowed_changes(dev1, project):
    """T-195: work ↔ work or Break, leave ↔ leave; anything else is refused and changes nothing."""
    posted = form(work(MONDAY, "09:00", "12:00", project), leave(TUESDAY, "8", "PTO", "Off"))
    source = key("PROJECT", project)
    grid = act(dev1, posted, "change", source, category="MEETING").context["grid"]
    assert [r.label for r in grid.rows] == ["Meetings", "PTO"] and grid.worked == 180
    grid = act(dev1, posted, "change", source, category="BREAK", project="9").context["grid"]
    assert [r.key for r in grid.rows] == ["BREAK:", "PTO:"] and grid.worked == 0  # not counted
    response = act(
        dev1, grid_post(grid), "change", "BREAK:", category="PROJECT", project=project.pk
    )
    assert response.context["grid"].worked == 180  # counted again
    grid = act(dev1, posted, "change", "PTO:", category="SICK").context["grid"]
    assert [r.label for r in grid.rows][1] == "Sick" and grid.rows[1].minutes == 480

    inactive = ProjectFactory(code="PRJ-009", name="Old", active=False)
    refused = {
        "a leave row can only change to another kind of leave": (source, {"category": "PTO"}),
        "only to work or Break": ("PTO:", {"category": "MEETING"}),
        "Choose a category.": (source, {"category": "NOPE"}),
        "Choose an active project.": (source, {"category": "PROJECT", "project": inactive.pk}),
        "Choose a row of this week.": ("NOPE:", {"category": "MEETING"}),
    }
    for message, (row, target) in refused.items():
        response = act(dev1, posted, "change", row, **target)
        assert response.status_code == 400 and message in response.content.decode(), message
    assert act(dev1, posted, "rename", source).status_code == 400
    assert not TimeEntry.objects.exists()


@pytest.mark.django_db(databases=["default", "payroll"])
def test_locked_and_other_peoples_weeks_are_refused(org, project, login_as, make_week, fixed_now):
    """T-196: row actions only where the grid is editable; checked on the server (403/405)."""
    posted = form(work(MONDAY, "09:00", "12:00", project))
    row = key("PROJECT", project)
    dev1 = login_as(org.dev1)
    sheet = make_week(org.dev1, OLDER_WEEK)  # SUBMITTED
    for week in (OLDER_WEEK, LAST_WEEK):  # submitted; not submitted and past its deadline
        assert act(dev1, posted, "delete", row, url=rows_url(week)).status_code == 403, week
    assert dev1.get(rows_url()).status_code == 405
    assert act(dev1, posted, "delete", row).status_code == 200  # the open week: allowed

    change = raise_request(org.dev1, OLDER_WEEK, "Monday is wrong", now=fixed_now)
    edit_url = reverse("request_rows", args=[change.pk])
    for person in (org.dev1, org.ops_manager):  # the employee themselves; a manager elsewhere
        response = act(login_as(person), posted, "delete", row, url=edit_url)
        assert response.status_code == 403, person.employee_code
    manager = login_as(org.manager)
    assert act(manager, posted, "delete", row, url=edit_url).status_code == 200
    reject_request(change, org.manager, "Looks right", now=fixed_now)
    assert act(manager, posted, "delete", row, url=edit_url).status_code == 403  # handled
    assert manager.get(edit_url).status_code == 405
    assert TimeEntry.objects.filter(timesheet=sheet).count() == 5  # never touched


def test_row_actions_in_edit_directly_are_audited(org, project, mobile, login_as, fixed_now):
    """T-197: Edit directly: change one row, delete another, save → one UPDATE audit row."""
    sheet = TimesheetFactory(employee=org.dev1, week_start=LAST_WEEK, status="SUBMITTED")
    monday = LAST_WEEK + timedelta(days=1)
    TimeEntryFactory(timesheet=sheet, work_date=monday, project=project)
    TimeEntryFactory(
        timesheet=sheet,
        work_date=monday + timedelta(days=1),
        category="MEETING",
        project=None,
        end_time=time(10),
        minutes=60,
        reason="Planning",
    )
    change = raise_request(org.dev1, LAST_WEEK, "Monday was on the mobile app", now=fixed_now)
    manager = login_as(org.manager)
    edit = reverse("request_edit", args=[change.pk])
    url = reverse("request_rows", args=[change.pk])
    page = manager.get(edit)
    assert f'data-rows-url="{url}"' in page.content.decode()
    grid = page.context["grid"]
    grid = act(
        manager, grid_post(grid), "change", key("PROJECT", project), url=url, category="PROJECT",
        project=mobile.pk,
    ).context["grid"]  # fmt: skip
    grid = act(manager, grid_post(grid), "delete", "MEETING:", url=url).context["grid"]
    assert [r.label for r in grid.rows] == ["PRJ-002 Mobile App / Project work"]
    assert not AuditLog.objects.filter(action="UPDATE").exists()  # nothing saved yet

    data = {**grid_post(grid), "note": "Moved Monday to the mobile app; dropped the meeting."}
    assert manager.post(edit, data).status_code == 302
    (row,) = AuditLog.objects.filter(action="UPDATE", entity_type="Timesheet")
    assert row.actor == org.manager and row.change_request_id == change.pk
    assert [(e["category"], e["project"]) for e in row.before["entries"]] == [
        ("PROJECT", "PRJ-001"),
        ("MEETING", None),
    ]
    assert [(e["category"], e["project"], e["start"], e["end"]) for e in row.after["entries"]] == [
        ("PROJECT", "PRJ-002", "09:00", "17:00")
    ]
    assert ChangeRequest.objects.get().status == "EDITED"
    assert Timesheet.objects.get().status == "SUBMITTED"


def test_row_action_markup(org, project, login_as, fixed_now, make_week):
    """T-199: ⋮ menu with a named button on editable grids only; choices fit the row's kind."""
    dev1 = login_as(org.dev1)
    posted = form(
        work(MONDAY, "09:00", "12:00", project, reason="Login"),
        work(MONDAY, "13:00", "17:00", project, reason=""),
        leave(TUESDAY, "8", "PTO", "Off"),
    )
    assert dev1.post(week_url(), posted).status_code == 302
    html = dev1.get(week_url()).content.decode()
    assert 'aria-label="Row actions for PRJ-001 Customer Portal"' in html
    assert 'aria-label="Row actions for PTO"' in html
    assert f'data-rows-url="{rows_url()}"' in html
    work_dialog = html.split(f'id="row-project-{project.pk}-change"')[1].split("</dialog>")[0]
    leave_dialog = html.split('id="row-pto-0-change"')[1].split("</dialog>")[0]
    for value in ("PROJECT", "MEETING", "TRAINING", "OTHER", "BREAK"):
        assert f'value="{value}"' in work_dialog and f'value="{value}"' not in leave_dialog
    for value in ("PTO", "SICK", "HOLIDAY"):
        assert f'value="{value}"' in leave_dialog and f'value="{value}"' not in work_dialog
    assert f'<option value="{project.pk}" selected>' in work_dialog
    delete = html.split(f'id="row-project-{project.pk}-delete"')[1].split("</dialog>")[0]
    assert "Delete PRJ-001 Customer Portal? This removes 2 time slots (7.00 h) from this week." in (
        delete
    )
    assert "This removes 1 leave entry (8.00 h)" in html
    reasons = re.findall(r'<input type="text" maxlength="255" [^>]*name="entry-\d+-reason"', html)
    assert len(reasons) == 3 and "readonly" not in "".join(reasons)  # every slot, editable

    make_week(org.dev1, OLDER_WEEK)  # submitted: read-only
    html = dev1.get(week_url(OLDER_WEEK)).content.decode()
    assert "Row actions for" not in html and "row-actions" not in html
