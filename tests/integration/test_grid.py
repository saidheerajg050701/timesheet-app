"""The weekly grid (Change 2, D-106–D-110): one row per Project / Category, Mon–Sun cells."""

import re
from datetime import date, time, timedelta

import pytest
from django.urls import reverse

from tests.factories import ProjectFactory, TimeEntryFactory, TimesheetFactory
from tests.forms import brk, form, leave, work
from timesheets.models import ChangeRequest, PeriodApproval, TimeEntry, Timesheet
from timesheets.services.summary import summarize
from timesheets.services.weeks import entries_snapshot

WEEK = date(2026, 10, 18)  # the current week (Sun–Sat) at fixed_now (Wed 21 Oct)
MONDAY, TUESDAY, WEDNESDAY = (WEEK + timedelta(days=n) for n in (1, 2, 3))
LAST_WEEK = date(2026, 10, 11)


@pytest.fixture
def dev1(org, login_as, fixed_now):
    return login_as(org.dev1)


def url(week=WEEK):
    return reverse("timesheet_week", args=[week])


def cell(category, project, day, task="DEV"):
    """A cell's id; project rows include their task (DEV unless told otherwise, D-152)."""
    part = f"-{task.lower()}" if project and task else ""
    return f"cell-{category.lower()}-{project.pk if project else 0}{part}-{day.isoformat()}"


def cell_hours(html, cell_id):
    return re.search(
        rf'aria-controls="{cell_id}"[^>]*>\s*<span class="cell-hours"[^>]*>([^<]*)<', html
    )[1]


def dialog(html, cell_id):
    return html.split(f'id="{cell_id}"')[1].split("</dialog>")[0]


def slots(html):
    return len(re.findall(r'class="grid-slot" data-index="\d+"', html))


def button(html, cell_id):
    """A cell's button, opening tag and contents."""
    return re.search(rf'<button[^>]*aria-controls="{cell_id}".*?</button>', html, re.S)[0]


def summary_row(html, heading):
    """A Day summary row's cells, Sun…Sat then the week: ["8:00", "0:00", …]."""
    row = html.split('id="day-summary"')[1].split(f">{heading}</th>")[1].split("</tr>")[0]
    return re.findall(r"<td[^>]*>([^<]*)</td>", row)


def entry(
    sheet,
    day,
    start=None,
    end=None,
    *,
    category="PROJECT",
    project=None,
    minutes=None,
    reason="Work",
):
    return TimeEntryFactory(
        timesheet=sheet,
        work_date=day,
        category=category,
        project=project,
        start_time=start,
        end_time=end,
        minutes=minutes
        if minutes is not None
        else (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute),
        reason=reason,
    )


@pytest.fixture
def mixed_week(org, project):
    """Two projects, a meeting, a break and PTO, with two slots in one cell."""
    other = ProjectFactory(number=2, name="Mobile App")
    sheet = TimesheetFactory(employee=org.dev1, week_start=WEEK, status="DRAFT")
    entry(sheet, MONDAY, time(9), time(12), project=project, reason="Login page")
    entry(sheet, MONDAY, time(12), time(12, 30), category="BREAK", reason="Lunch")
    entry(sheet, MONDAY, time(12, 30), time(13), category="MEETING", reason="Stand-up")
    entry(sheet, MONDAY, time(13), time(17), project=project, reason="Code review")
    entry(sheet, TUESDAY, category="PTO", minutes=480, reason="Vacation")
    entry(sheet, WEDNESDAY, time(9), time(15, 15), project=other, reason="Release")
    return sheet, other


def test_grid_layout_and_totals(dev1, project, mixed_week):
    """T-160: one row per Project/Category in order; day headers; cell, row and footer totals."""
    sheet, other = mixed_week
    response = dev1.get(url())
    html = response.content.decode()
    grid = response.context["grid"]
    assert [r.label for r in grid.rows] == [
        "I-001 Customer Portal · DEV Development",
        "I-002 Mobile App · DEV Development",
        "Meetings",
        "Break (unpaid)",
        "PTO",
    ]
    assert (
        '<span class="grid-dayname">Mon</span><span class="grid-date">Oct 19, 2026</span>' in html
        and html.index('<span class="grid-dayname">Sun</span><span class="grid-date">Oct 18, 2026')
        < html.index('<span class="grid-dayname">Sat</span><span class="grid-date">Oct 24, 2026')
    )
    assert ">Total worked hours</th>" in html
    assert cell_hours(html, cell("PROJECT", project, MONDAY)) == "7.00"  # two slots
    assert cell_hours(html, cell("BREAK", None, MONDAY)) == "0.50"
    assert cell_hours(html, cell("PTO", None, TUESDAY)) == "8.00"
    assert cell_hours(html, cell("PROJECT", project, TUESDAY)) == ""
    assert [r.minutes for r in grid.rows] == [420, 375, 30, 30, 480]
    assert [minutes for _, minutes, _ in grid.footer] == [0, 450, 0, 375, 0, 0, 0]  # Sun…Sat
    assert grid.worked == 825 and 'data-role="week-total">13.75<' in html
    assert "not counted</span>" in html and ">leave</span>" in html
    assert html.index('id="entries"') < html.index('id="day-summary"')  # summary stays below
    summary = summarize(list(sheet.entries.all()), sheet.employee, WEEK)
    assert [d.worked for d in summary.days] == [minutes for _, minutes, _ in grid.footer]


def test_add_row(dev1, project):
    """T-161: "+ Add row" gives an empty row for a category or active project; kept on error."""
    row_url = reverse("timesheet_row", args=[WEEK])
    html = dev1.get(row_url, {"category": "MEETING", "project": "9"}).content.decode()
    assert 'data-row-key="MEETING:"' in html and html.count('class="cell-button"') == 7
    task = {"category": "PROJECT", "project": project.pk, "task": "DEV"}  # Change 10: with a task
    html = dev1.get(row_url, task).content.decode()
    assert f'data-row-key="PROJECT:{project.pk}:DEV"' in html and "I-001 Customer Portal" in html
    assert dev1.get(row_url, {"category": "NOPE"}).status_code == 400
    assert dev1.get(row_url, {"category": "PROJECT"}).status_code == 400
    project.active = False
    project.save()
    assert dev1.get(row_url, {"category": "PROJECT", "project": project.pk}).status_code == 400

    posted = form(work(MONDAY, "09:00", "12:00", category="MEETING", reason="x" * 256))
    posted["grid-row"] = ["MEETING:", "TRAINING:", "BOGUS:", "PTO:x"]
    html = dev1.post(url(), posted).content.decode()
    assert "longer than 255 characters" in html
    assert 'data-row-key="TRAINING:"' in html  # added, no slots yet: kept through the error
    assert "BOGUS" not in html and 'data-row-key="PTO:' not in html
    assert html.count('data-row-key="MEETING:"') == 1  # never twice


def test_multi_slot_cell(dev1, org, project):
    """T-162: two slots in one cell save as two entries and show again with times and reasons."""
    posted = form(
        work(MONDAY, "08:00", "12:00", project, reason="Login page"),
        work(MONDAY, "13:00", "17:30", project, reason="Code review"),
    )
    assert dev1.post(url(), posted).status_code == 302
    assert TimeEntry.objects.filter(work_date=MONDAY).count() == 2
    html = dev1.get(url()).content.decode()
    target = cell("PROJECT", project, MONDAY)
    assert cell_hours(html, target) == "8.50"
    panel = dialog(html, target)
    assert slots(panel) == 2
    for text in (
        'value="08:00"',
        'value="12:00"',
        'value="13:00"',
        'value="17:30"',
        "Login page",
        "Code review",
    ):
        assert text in panel


def test_leave_cell(dev1, org):
    """T-163: a leave cell has hours and a reason, no times; it is never in Total worked hours."""
    assert dev1.post(url(), form(leave(TUESDAY, "7.5", "SICK", "Doctor"))).status_code == 302
    saved = TimeEntry.objects.get()
    assert (saved.minutes, saved.start_time, saved.end_time) == (450, None, None)
    response = dev1.get(url())
    html = response.content.decode()
    target = cell("SICK", None, TUESDAY)
    panel = dialog(html, target)
    assert (
        'name="entry-0-hours" value="7.50"' in panel and "-start" not in panel.split("<template")[0]
    )
    assert cell_hours(html, target) == "7.50" and ">leave</span>" in html
    assert response.context["grid"].worked == 0  # leave is shown, not worked
    assert 'id="week-leave">7:30<' in html and 'id="week-worked">0:00<' in html


def test_overlap_error_is_shown_on_the_right_cells(dev1, project):
    """T-164: overlapping slots in two rows: nothing saved; both cells marked, message inside."""
    posted = form(
        work(MONDAY, "09:00", "12:00", project),
        work(MONDAY, "11:00", "13:00", category="MEETING", reason="Planning"),
        work(TUESDAY, "09:00", "10:00", project),
    )
    html = dev1.post(url(), posted).content.decode()
    assert not TimeEntry.objects.exists()
    message = "Mon 19 Oct: 09:00–12:00 I-001-DEV and 11:00–13:00 Meetings overlap."
    for target in (cell("PROJECT", project, MONDAY), cell("MEETING", None, MONDAY)):
        assert re.search(rf'aria-controls="{target}"[^>]*aria-invalid="true"', html)
        assert message in dialog(html, target)
    label = "I-001 Customer Portal · DEV Development, Tue Oct 20: 1.00 hours, 1 slot"
    assert f'aria-label="{label}">' in html  # an unaffected cell keeps its slot, not marked
    summary = html.split('id="errors"')[1].split("</div>")[0]
    assert message in summary and 'data-grid-action="open"' in summary


@pytest.mark.django_db(databases=["default", "payroll"])
def test_read_only_grids(org, project, login_as, make_week, fixed_now):
    """T-165: submitted, request, approval and Team week grids: no inputs; dialogs list slots."""
    make_week(org.dev1, LAST_WEEK)
    sheet = make_week(org.dev1, date(2026, 9, 27))
    make_week(org.dev1, date(2026, 10, 4))
    change = ChangeRequest.objects.create(timesheet=sheet, requester=org.dev1, reason="Fix")
    PeriodApproval.objects.create(employee=org.dev1, period_start=date(2026, 9, 27))
    pages = [
        (org.dev1, url(LAST_WEEK)),
        (org.manager, reverse("request_detail", args=[change.pk])),
        (org.manager, reverse("approval_detail", args=[date(2026, 9, 27), "DEV1"])),
        (org.manager, reverse("team_member_week", args=["DEV1", LAST_WEEK])),
    ]
    for person, page_url in pages:
        html = login_as(person).get(page_url).content.decode()
        grid = html.split('class="table week-grid')[1].split("</table>\n  </div>")[0]
        assert "<input" not in grid and "<select" not in grid and "<template" not in grid, page_url
        assert "cell-slots-readonly" in grid and "09:00" in grid and "Feature development" in grid
        assert "+ Add row" not in html


def test_existing_week_renders_the_same(dev1, org, project, mixed_week):
    """T-166: an existing week opens unchanged; totals match summarize; a no-op save keeps all."""
    sheet, _ = mixed_week
    before_entries = entries_snapshot(sheet.entries.select_related("project"))
    first = dev1.get(url())
    html = first.content.decode()
    day_summary = html.split('id="day-summary"')[1].split("</table>")[0]
    grid = first.context["grid"]
    summary = summarize(list(sheet.entries.all()), org.dev1, WEEK)
    assert grid.worked == summary.worked
    assert sum(r.minutes for r in grid.rows if r.kind == "break") == summary.breaks
    assert sum(r.minutes for r in grid.rows if r.kind == "leave") == summary.leave
    assert slots(html) == sheet.entries.count()

    data = {"action": "save", "grid-row": [r.key for r in grid.rows]}
    for row in grid.rows:
        for c in row.cells:
            for s in c.slots:
                data.update({
                    f"entry-{s.index}-date": s.work_date, f"entry-{s.index}-category": s.category,
                    f"entry-{s.index}-project": s.project, f"entry-{s.index}-task": s.task,
                    f"entry-{s.index}-start": s.start,
                    f"entry-{s.index}-end": s.end, f"entry-{s.index}-hours": s.hours,
                    f"entry-{s.index}-reason": s.reason,
                })  # fmt: skip
    assert dev1.post(url(), data).status_code == 302
    sheet.refresh_from_db()
    assert entries_snapshot(sheet.entries.select_related("project")) == before_entries
    again = dev1.get(url())
    assert again.content.decode().split('id="day-summary"')[1].split("</table>")[0] == day_summary
    assert [m for _, m, _ in again.context["grid"].footer] == [m for _, m, _ in grid.footer]


def two_slots_and_a_break(project, *more):
    """The reported case (D-127): one project around a break, all on Sunday."""
    return form(
        work(WEEK, "08:00", "13:00", project, reason="Login page"),
        brk(WEEK, "13:00", "14:00"),
        work(WEEK, "14:00", "17:00", project, reason="Code review"),
        *more,
    )


def test_two_slots_for_one_project_on_one_day(dev1, project):
    """T-184: 08:00–13:00 and 14:00–17:00 for one project around a 13:00–14:00 Break."""
    assert dev1.post(url(), two_slots_and_a_break(project)).status_code == 302
    assert TimeEntry.objects.filter(work_date=WEEK).count() == 3
    response = dev1.get(url())
    html = response.content.decode()
    grid = response.context["grid"]
    assert [r.label for r in grid.rows] == [
        "I-001 Customer Portal · DEV Development",
        "Break (unpaid)",
    ]  # one row for the project, not two
    target = cell("PROJECT", project, WEEK)
    assert cell_hours(html, target) == "8.00"
    assert cell_hours(html, cell("BREAK", None, WEEK)) == "1.00" and "not counted</span>" in html
    assert slots(dialog(html, target)) == 2
    assert grid.footer[0][1] == 480 and 'data-role="week-total">8.00<' in html
    assert summary_row(html, "Hours worked")[0] == "8:00"  # Sunday
    assert summary_row(html, "Break (unpaid)")[0] == "1:00"
    assert 'id="week-worked">8:00<' in html and 'id="week-break">1:00<' in html


def test_overlapping_third_slot_is_refused_on_its_cell(dev1, project):
    """T-185: a third slot 16:00–18:00 overlapping 14:00–17:00 is refused on the project cell."""
    assert dev1.post(url(), two_slots_and_a_break(project)).status_code == 302
    before = entries_snapshot(TimeEntry.objects.select_related("project"))
    posted = two_slots_and_a_break(project, work(WEEK, "16:00", "18:00", project, reason="Demo"))
    response = dev1.post(url(), posted)
    html = response.content.decode()
    assert response.status_code == 200  # shown again, not saved
    assert entries_snapshot(TimeEntry.objects.select_related("project")) == before
    message = "Sun 18 Oct: 14:00–17:00 I-001-DEV and 16:00–18:00 I-001-DEV overlap."
    target = cell("PROJECT", project, WEEK)
    assert re.search(rf'aria-controls="{target}"[^>]*aria-invalid="true"', html)
    assert message in dialog(html, target) and slots(dialog(html, target)) == 3
    assert 'aria-invalid="true"' not in button(html, cell("BREAK", None, WEEK))
    summary = html.split('id="errors"')[1].split("</div>")[0]
    assert message in summary


@pytest.mark.django_db(databases=["default", "payroll"])
def test_multi_slot_hint(org, project, login_as, fixed_now):
    """T-186: "8.00 · 2 slots" with the slot times as title, editable and read-only; not for one."""
    client = login_as(org.dev1)
    assert client.post(url(), two_slots_and_a_break(project)).status_code == 302
    hint = '<span class="cell-meta" data-role="cell-meta" aria-hidden="true"> · 2 slots</span>'
    times = "08:00–13:00, 14:00–17:00"
    sheet = TimesheetFactory(employee=org.dev1, week_start=LAST_WEEK, status="SUBMITTED")
    entry(sheet, LAST_WEEK, time(8), time(13), project=project, reason="Login page")
    entry(sheet, LAST_WEEK, time(14), time(17), project=project, reason="Code review")
    entry(sheet, LAST_WEEK + timedelta(days=1), time(9), time(17), project=project)
    pages = [
        (org.dev1, url(), WEEK, True),  # editable
        (org.dev1, url(LAST_WEEK), LAST_WEEK, False),  # submitted: read-only
        (org.manager, reverse("team_member_week", args=["DEV1", LAST_WEEK]), LAST_WEEK, False),
    ]
    for person, page_url, day, editable in pages:
        html = login_as(person).get(page_url).content.decode()
        two = button(html, cell("PROJECT", project, day))
        assert hint in two and '<span class="cell-hours" data-role="cell-hours">8.00</span>' in two
        assert f'title="{times}"' in two, page_url
        assert f"8.00 hours, 2 slots ({times})" in two
        grid = html.split('class="table week-grid')[1].split("</table>\n  </div>")[0]
        assert ("<input" in grid) is editable
        panel = dialog(html, cell("PROJECT", project, day))
        assert "Login page" in panel and "Code review" in panel
    html = login_as(org.dev1).get(url(LAST_WEEK)).content.decode()
    one = button(html, cell("PROJECT", project, LAST_WEEK + timedelta(days=1)))
    assert "title=" not in one and "slots" not in one  # a single slot has no hint
    assert 'aria-hidden="true"></span>' in one and '8.00 hours, 1 slot"' in one
    html = login_as(org.dev1).get(url()).content.decode()
    assert "+ Add another time slot" in html


def test_week_without_reasons(dev1, org, project):
    """T-188: slots without a reason save and submit; read-only cells show reasons only if any."""
    rows = (
        work(MONDAY, "09:00", "12:00", project, reason=""),
        {**brk(MONDAY, "12:00", "12:30"), "reason": ""},
        work(MONDAY, "12:30", "17:00", project, reason="   "),  # only spaces: saved blank
        leave(TUESDAY, "8", "PTO", ""),
        work(WEDNESDAY, "09:00", "12:00", project, reason="Release"),
        work(WEDNESDAY, "13:00", "17:00", project, reason=""),
    )
    assert dev1.post(url(), form(*rows)).status_code == 302
    reasons = sorted(TimeEntry.objects.values_list("reason", flat=True))
    assert reasons == ["", "", "", "", "", "Release"]
    assert dev1.post(url(), form(*rows, action="submit")).status_code == 302
    assert Timesheet.objects.get(employee=org.dev1).status == "SUBMITTED"

    html = dev1.get(url()).content.decode()
    assert "<input" not in html.split('class="table week-grid')[1].split("</table>\n  </div>")[0]
    for target in (cell("PROJECT", project, MONDAY), cell("PTO", None, TUESDAY)):
        panel = dialog(html, target)
        assert "cell-slots-readonly" in panel and ">Reason<" not in panel, target
    assert "12:30" in dialog(html, cell("PROJECT", project, MONDAY))
    mixed = dialog(html, cell("PROJECT", project, WEDNESDAY))
    assert '<th scope="col">Reason</th>' in mixed and "<td>Release</td>" in mixed
    assert mixed.count("<td></td>") == 1  # the slot without a reason: an empty cell
