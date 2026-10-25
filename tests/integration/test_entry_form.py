"""The entry-row form shared by the employee's week page and Edit directly (Phase 5b/6)."""

import re
from datetime import date, time

import pytest
from django.urls import reverse

from tests.factories import TimeEntryFactory, TimesheetFactory
from tests.forms import brk, form, work
from timesheets.models import ChangeRequest, TimeEntry

THIS_WEEK = date(2026, 10, 18)  # employee page: current week (fixed_now is Wed 21 Oct)
LAST_WEEK = date(2026, 10, 11)  # Edit directly: dev1's submitted week with an open request
FRIDAY = {THIS_WEEK: date(2026, 10, 23), LAST_WEEK: date(2026, 10, 16)}


@pytest.fixture(params=["employee page", "edit directly"])
def page(request, org, project, login_as, fixed_now):
    """(client, url, week) for either form, each starting with one saved row 08:30–12:00."""
    if request.param == "employee page":
        sheet = TimesheetFactory(employee=org.dev1, week_start=THIS_WEEK, status="DRAFT")
        client, url = login_as(org.dev1), reverse("timesheet_week", args=[THIS_WEEK])
    else:
        sheet = TimesheetFactory(employee=org.dev1, week_start=LAST_WEEK, status="SUBMITTED")
        change = ChangeRequest.objects.create(timesheet=sheet, requester=org.dev1, reason="Fix")
        client, url = login_as(org.manager), reverse("request_edit", args=[change.pk])
    day = FRIDAY[sheet.week_start]
    TimeEntryFactory(
        timesheet=sheet,
        work_date=day,
        project=project,
        start_time=time(8, 30),
        end_time=time(12),
        minutes=210,
    )
    return client, url, sheet.week_start


def slot_count(html):
    """Slots shown in the grid (each cell's empty template slot has no number yet)."""
    return len(re.findall(r'class="grid-slot" data-index="\d+"', html))


def cell_hours(html):
    """{cell id: hours shown on its button} for every cell with time."""
    return dict(
        re.findall(
            r'aria-controls="(cell-[^"]+)"[^>]*>\s*<span class="cell-hours"[^>]*>([^<]+)<', html
        )
    )


FIELDS = {
    "date": "work_date",
    "category": "category",
    "project": "project",
    "start": "start",
    "end": "end",
    "hours": "hours",
    "reason": "reason",
}


def browser_post(response, **changes):
    """What the browser sends back: every slot of the grid exactly as rendered, plus its rows."""
    grid = response.context["grid"]
    data = {"action": "save", "grid-row": [row.key for row in grid.rows]}
    for row in grid.rows:
        for cell in row.cells:
            for slot in cell.slots:
                data.update(
                    {f"entry-{slot.index}-{f}": getattr(slot, a) for f, a in FIELDS.items()}
                )
    data.update(changes)
    return data


def test_completely_empty_rows_are_ignored(page, project):
    """T-89: no blank slots in the grid; an empty entry is ignored, a partial one refused."""
    client, url, week = page
    friday = FRIDAY[week]
    # An entry with only hours, or only a reason, is not empty: it is checked and refused.
    for field, value in (("hours", "2"), ("reason", "Forgot this")):
        partial = {"date": friday.isoformat(), field: value}
        bad = form(work(friday, "08:30", "12:00", project), partial)
        assert "choose a category" in client.post(url, bad).content.decode()

    page_load = client.get(url)
    assert slot_count(page_load.content.decode()) == 1  # the saved entry only, no blank slots
    data = browser_post(page_load, **{"entry-0-reason": "Release work"})
    data["entry-7-date"] = friday.isoformat()  # an entry with nothing typed: ignored
    response = client.post(url, data)
    assert response.status_code == 302
    saved = TimeEntry.objects.get(timesheet__week_start=week)
    assert saved.reason == "Release work"


def test_rerender_after_an_error_adds_no_rows(page, project):
    """T-90: re-rendering after a failed save shows exactly the posted slots and rows."""
    client, url, week = page
    friday = FRIDAY[week]
    data = browser_post(client.get(url), **{"entry-0-reason": ""})  # missing reason → error
    data["grid-row"] = data["grid-row"] + ["MEETING:"]  # a row added without slots yet
    data.update({f"entry-5-{k}": v for k, v in brk(friday, "12:00", "12:30").items()})
    first = client.post(url, data)
    html = first.content.decode()
    assert "a reason is required" in html and slot_count(html) == 2
    assert 'data-row-key="MEETING:"' in html  # the empty new row is kept
    second = client.post(url, browser_post(first)).content.decode()
    assert "a reason is required" in second and slot_count(second) == 2
    assert "choose a category" not in second


def test_hours_are_shown_for_every_row(page, project):
    """T-91: each cell shows its hours (2 decimals) on page load and after an error (both forms)."""
    client, url, week = page
    friday = FRIDAY[week]
    project_cell = f"cell-project-{project.pk}-{friday.isoformat()}"
    assert cell_hours(client.get(url).content.decode()) == {project_cell: "3.50"}  # 08:30–12:00
    rows = form(
        work(friday, "08:30", "12:00", project),
        brk(friday, "12:00", "12:45"),
        work(friday, "12:45", "17:15", category="MEETING", reason=""),  # error: no reason
        {"date": friday.isoformat(), "category": "PTO", "hours": "1.5", "reason": "Leave early"},
    )
    after_error = client.post(url, rows).content.decode()
    assert "a reason is required" in after_error
    day = friday.isoformat()
    assert cell_hours(after_error) == {
        project_cell: "3.50",
        f"cell-break-0-{day}": "0.75",
        f"cell-meeting-0-{day}": "4.50",
        f"cell-pto-0-{day}": "1.50",
    }
    meeting = f"cell-meeting-0-{day}"
    assert re.search(rf'aria-controls="{meeting}"[^>]*aria-invalid="true"', after_error)


def test_grid_script_keeps_totals_live():
    """Helper check: the grid script recalculates totals while typing and guards unsaved work."""
    from pathlib import Path

    script = Path("static/js/grid.js").read_text()
    assert 'addEventListener("input"' in script and "toFixed(2)" in script
    assert "beforeunload" in script and "showModal" in script
