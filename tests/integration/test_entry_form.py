"""The entry-row form shared by the employee's week page and Edit directly (Phase 5b/6)."""

import re
from datetime import date, time

import pytest
from django.urls import reverse

from tests.factories import TimeEntryFactory, TimesheetFactory
from tests.forms import brk, form, work
from timesheets.models import ChangeRequest, TimeEntry

THIS_WEEK = date(2026, 10, 19)  # employee page: current week (fixed_now is Wed 21 Oct)
LAST_WEEK = date(2026, 10, 12)  # Edit directly: dev1's submitted week with an open request
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


def row_count(html):
    return len(re.findall(r'<tr id="row-', html))


def hours_values(html):
    return dict(re.findall(r'name="entry-(\d+)-hours" value="([^"]*)"', html))


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
    """What the browser sends back: every row exactly as rendered, untouched blanks included."""
    data = {"action": "save"}
    for row in response.context["rows"]:
        data.update({f"entry-{row.index}-{f}": getattr(row, a) for f, a in FIELDS.items()})
    data.update(changes)
    return data


def test_completely_empty_rows_are_ignored(page, project):
    """T-89: rows with nothing typed (day pre-filled only) are ignored on save, on both forms."""
    client, url, week = page
    friday = FRIDAY[week]
    # A row with only hours, or only a reason, is not empty: it is checked and refused.
    for field, value in (("hours", "2"), ("reason", "Forgot this")):
        partial = {"date": friday.isoformat(), field: value}
        bad = form(work(friday, "08:30", "12:00", project), partial)
        assert "choose a category" in client.post(url, bad).content.decode()

    page_load = client.get(url)
    assert row_count(page_load.content.decode()) == 3  # one saved row + two blank, day filled
    data = browser_post(page_load, **{"entry-0-reason": "Release work"})
    assert data["entry-1-date"] == data["entry-2-date"] == friday.isoformat()
    response = client.post(url, data)
    assert response.status_code == 302
    saved = TimeEntry.objects.get(timesheet__week_start=week)
    assert saved.reason == "Release work"


def test_rerender_after_an_error_adds_no_rows(page, project):
    """T-90: re-rendering after a failed save shows the posted rows only — no extra blanks."""
    client, url, week = page
    data = browser_post(client.get(url), **{"entry-0-reason": ""})  # missing reason → error
    first = client.post(url, data)
    html = first.content.decode()
    assert "a reason is required" in html and row_count(html) == 3
    second = client.post(url, browser_post(first)).content.decode()
    assert "a reason is required" in second and row_count(second) == 3
    assert "choose a category" not in second  # the blank rows were ignored both times


def test_hours_are_shown_for_every_row(page, project):
    """T-91: Hours is calculated for every timed row on load and after an error (both forms)."""
    client, url, week = page
    html = client.get(url).content.decode()
    assert hours_values(html)["0"] == "3.50"  # 08:30–12:00 on page load
    friday = FRIDAY[week]
    rows = form(
        work(friday, "08:30", "12:00", project),
        brk(friday, "12:00", "12:45"),
        work(friday, "12:45", "17:15", category="MEETING", reason=""),  # error: no reason
        {"date": friday.isoformat(), "category": "PTO", "hours": "1.5", "reason": "Leave early"},
    )
    after_error = client.post(url, rows).content.decode()
    assert "a reason is required" in after_error
    assert hours_values(after_error) == {"0": "3.50", "1": "0.75", "2": "4.50", "3": "1.5"}
    assert "readonly" in after_error.split('name="entry-0-hours"')[1].split(">")[0]
    assert (
        "readonly" not in after_error.split('name="entry-3-hours"')[1].split(">")[0]
    )  # leave: typed


def test_hours_script_calculates_while_typing():
    """Helper check: the shared script fills Hours from start/end as the user types."""
    from pathlib import Path

    script = Path("static/js/timesheet.js").read_text()
    assert 'addEventListener("input"' in script and "toFixed(2)" in script
    assert "el.readOnly = timed" in script
