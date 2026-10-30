"""Browser tests: the weekly grid — slots, rows, row menus, tasks, project search, deadlines."""

import re
from datetime import datetime, time, timedelta

import pytest
from django.urls import reverse
from playwright.sync_api import expect

from tests.e2e.conftest import E2E, THIS_WEEK, TZ
from tests.e2e.helpers import (
    BREAK,
    MONDAY,
    PORTAL,
    add_row,
    cell,
    menu_item,
    open_cell,
    pick_project,
    row_menu,
    status_of,
    week_url,
)
from tests.factories import (
    ProjectFactory,
)
from timesheets.models import TimeEntry

pytestmark = E2E


def test_save_draft_then_submit_before_the_deadline(e2e_org, open_as):
    """T-147: E2E save a draft with two slots around a break, reopen it, then submit in time."""
    page = open_as(e2e_org.dev1)
    page.goto(week_url(THIS_WEEK))
    expect(status_of(page)).to_have_text("Not started")
    add_row(page, "Project work", "I-001 Customer Portal")
    panel = open_cell(page, PORTAL, MONDAY)
    panel.get_by_label("Start").fill("08:00")
    panel.get_by_label("End").fill("13:00")
    panel.get_by_label("Reason").fill("Login page")
    panel.get_by_role("button", name="Done").click()
    expect(cell(page, PORTAL, MONDAY)).to_have_text("5.00")
    add_row(page, "Break time")
    panel = open_cell(page, BREAK, MONDAY)
    panel.get_by_label("Start").fill("13:00")
    panel.get_by_label("End").fill("14:00")
    panel.get_by_label("Reason").fill("Lunch")
    panel.get_by_role("button", name="Done").click()

    add_row(page, "Project work", "I-001 Customer Portal")  # again: points at its row (D-127)
    expect(page.locator("[data-week-grid]").get_by_role("status")).to_contain_text(
        "already has a row"
    )
    panel = open_cell(page, PORTAL, MONDAY)  # lists the slot and offers an empty one
    expect(panel.locator(".grid-slot")).to_have_count(2)
    expect(panel.get_by_label("Start").nth(1)).to_be_focused()
    panel.get_by_label("Start").nth(1).fill("14:00")
    panel.get_by_label("End").nth(1).fill("17:00")
    panel.get_by_label("Reason").nth(1).fill("Code review")
    panel.get_by_role("button", name="Done").click()
    expect(cell(page, PORTAL, MONDAY)).to_have_text("8.00 · 2 slots")
    expect(page.locator("#entries [data-role=week-total]")).to_have_text("8.00")  # Break not in it
    page.get_by_role("button", name="Save draft").click()
    expect(status_of(page)).to_have_text("Draft")
    assert TimeEntry.objects.count() == 3

    page.goto(week_url(THIS_WEEK))  # reopened: both slots are still there
    expect(cell(page, PORTAL, MONDAY)).to_have_text("8.00 · 2 slots")
    expect(cell(page, PORTAL, MONDAY)).to_have_attribute("title", "08:00–13:00, 14:00–17:00")
    panel = open_cell(page, PORTAL, MONDAY)
    expect(panel.get_by_label("Reason").first).to_have_value("Login page")
    expect(panel.get_by_label("Reason").nth(1)).to_have_value("Code review")
    panel.get_by_role("button", name="Done").click()
    expect(cell(page, PORTAL, MONDAY)).to_have_text("8.00 · 2 slots")  # the offered slot dropped
    page.get_by_role("button", name="Submit").click()
    expect(status_of(page)).to_have_text("Submitted")
    expect(page.get_by_role("button", name="Save draft")).to_have_count(0)
    expect(page.locator("#entries input")).to_have_count(0)  # read-only now
    expect(cell(page, PORTAL, MONDAY)).to_have_text("8.00 · 2 slots")
    panel = open_cell(page, PORTAL, MONDAY)
    expect(panel).to_contain_text("Login page")
    expect(panel).to_contain_text("14:00")


def test_week_locks_after_the_deadline(e2e_org, make_week, open_as, clock):
    """T-148: E2E an unsubmitted week is locked from Saturday 12:00 (fixed clock)."""
    make_week(e2e_org.dev1, THIS_WEEK, status="DRAFT")
    page = open_as(e2e_org.dev1)
    page.goto(week_url(THIS_WEEK))
    expect(page.get_by_role("button", name="Submit")).to_be_visible()

    clock.move_to(datetime(2026, 10, 24, 12, 0, tzinfo=TZ))  # Saturday 12:00
    page.goto(week_url(THIS_WEEK))
    expect(status_of(page)).to_have_text("Locked")
    expect(page.get_by_role("button", name="Submit")).to_have_count(0)
    expect(page.get_by_role("button", name="Save draft")).to_have_count(0)
    expect(page.locator("#entries input")).to_have_count(0)
    expect(page.locator("#entries")).to_contain_text("Feature work")


def test_weekly_grid_in_the_browser(e2e_org, make_week, open_as):
    """T-167: E2E grid: add rows, two slots by keyboard, live totals, unsaved warning, narrow."""
    page = open_as(e2e_org.dev1)
    page.goto(week_url(THIS_WEEK))
    add_row(page, "Project work", "I-001 Customer Portal")
    add_row(page, "Project work", "I-001 Customer Portal")  # no second row (D-127, T-183)
    expect(page.locator("dialog[open]")).to_have_count(0)
    expect(page.locator('#entries tr[data-row-key^="PROJECT:"]')).to_have_count(1)

    tuesday = THIS_WEEK + timedelta(days=2)
    button = cell(page, PORTAL, tuesday)
    button.focus()
    page.keyboard.press("Enter")  # cells are buttons: the keyboard opens them
    panel = page.locator("dialog[open]")
    panel.get_by_label("Start").fill("08:00")
    panel.get_by_label("End").fill("12:00")
    panel.get_by_label("Reason").fill("Bug fixes")
    expect(button).to_have_text("4.00")  # live while typing
    panel.get_by_role("button", name="+ Add another time slot").click()
    panel.get_by_label("Start").nth(1).fill("13:00")
    panel.get_by_label("End").nth(1).fill("17:30")
    panel.get_by_label("Reason").nth(1).fill("Code review")
    page.keyboard.press("Escape")  # Esc closes; focus goes back to the cell
    expect(page.locator("dialog[open]")).to_have_count(0)
    expect(button).to_be_focused()
    expect(button).to_contain_text("8.50")
    expect(page.locator("#entries [data-role=week-total]")).to_have_text("8.50")

    add_row(page, "PTO")
    panel = open_cell(page, "PTO", tuesday + timedelta(days=1))
    panel.get_by_label("Hours").fill("8")
    panel.get_by_label("Reason").fill("Vacation")
    panel.get_by_role("button", name="Done").click()
    expect(page.locator("#entries [data-role=week-total]")).to_have_text("8.50")  # leave not in it

    warnings = []
    page.on("dialog", lambda dialog: warnings.append(dialog.type))
    page.get_by_role("link", name="Dashboard").click()  # unsaved changes: the browser asks first
    expect(page).to_have_url(re.compile(r"/$"))
    assert "beforeunload" in warnings
    page.goto(week_url(THIS_WEEK))
    assert TimeEntry.objects.count() == 0  # nothing was saved by leaving

    add_row(page, "Project work", "I-001 Customer Portal")
    panel = open_cell(page, PORTAL, tuesday)
    panel.get_by_label("Start").fill("09:00")
    panel.get_by_label("End").fill("12:00")
    panel.get_by_label("Reason").fill("Bug fixes")
    panel.get_by_role("button", name="Done").click()
    page.get_by_role("button", name="Save draft").click()
    expect(status_of(page)).to_have_text("Draft")
    assert TimeEntry.objects.count() == 1

    page.set_viewport_size({"width": 390, "height": 844})
    scroller = page.locator(".grid-scroll")
    assert scroller.evaluate("e => e.scrollWidth > e.clientWidth")  # the grid scrolls sideways
    assert page.evaluate("() => { scrollTo(5000, 0); return scrollX; }") == 0  # the page doesn't
    first = page.locator("#entries tbody th.grid-label").first
    scroller.evaluate("e => e.scrollLeft = 300")
    assert first.evaluate("e => getComputedStyle(e).position") == "sticky"
    box = first.bounding_box()
    assert box["x"] < 20  # still at the left edge while the days scroll


def test_add_row_for_an_existing_row_points_at_it(e2e_org, open_as):
    """T-183: E2E "+ Add row" for a row already there: no error, it is highlighted and focused."""
    page = open_as(e2e_org.dev1)
    page.goto(week_url(THIS_WEEK))
    add_row(page, "Project work", "I-001 Customer Portal")
    add_row(page, "Meetings")
    add_row(page, "Project work", "I-001 Customer Portal")
    expect(page.locator("dialog[open]")).to_have_count(0)  # closed; no error to dismiss
    expect(page.get_by_role("alert")).to_have_count(0)
    expect(page.locator("[data-week-grid]").get_by_role("status")).to_have_text(
        "I-001 Customer Portal · DEV Development already has a row. Click a day to add another "
        "time slot (for example 2:00 PM – 5:00 PM)."
    )
    rows = page.locator("#entries tr.grid-row")
    expect(rows).to_have_count(2)
    expect(page.locator('#entries tr[data-row-key^="PROJECT:"]')).to_have_count(1)
    portal = page.locator('#entries tr[data-row-key^="PROJECT:"]')  # the I-001 row
    expect(portal).to_have_class(re.compile(r"\bis-highlighted\b"))
    expect(cell(page, PORTAL, THIS_WEEK)).to_be_focused()  # its first day, Sunday
    expect(portal).not_to_have_class(re.compile(r"\bis-highlighted\b"), timeout=5000)  # brief

    add_row(page, "PTO")
    add_row(page, "PTO")  # leave rows get the leave wording
    expect(page.locator("[data-week-grid]").get_by_role("status")).to_have_text(
        "PTO already has a row. Click a day to enter or change its hours."
    )
    expect(cell(page, "PTO", THIS_WEEK)).to_be_focused()
    expect(rows).to_have_count(3)
    assert TimeEntry.objects.count() == 0  # nothing saved by any of this


def test_time_without_a_reason(e2e_org, open_as):
    """T-190: E2E time entered without a reason saves and submits; no empty Reason shown."""
    page = open_as(e2e_org.dev1)
    page.goto(week_url(THIS_WEEK))
    add_row(page, "Project work", "I-001 Customer Portal")
    panel = open_cell(page, PORTAL, MONDAY)
    expect(panel.get_by_label("Reason")).to_be_visible()  # still offered, just optional
    panel.get_by_label("Start").fill("09:00")
    panel.get_by_label("End").fill("17:00")
    panel.get_by_role("button", name="Done").click()
    expect(cell(page, PORTAL, MONDAY)).to_have_text("8.00")
    page.get_by_role("button", name="Save draft").click()
    expect(status_of(page)).to_have_text("Draft")
    expect(page.locator("#errors")).to_have_count(0)
    assert TimeEntry.objects.get().reason == ""

    page.get_by_role("button", name="Submit").click()
    expect(status_of(page)).to_have_text("Submitted")
    panel = open_cell(page, PORTAL, MONDAY)
    expect(panel).to_contain_text("09:00")
    expect(panel).to_contain_text("17:00")
    expect(panel.get_by_role("columnheader", name="Reason")).to_have_count(0)


def test_change_and_delete_rows(e2e_org, open_as):
    """T-200: E2E move a wrong row to another project, then delete a row; totals follow."""
    ProjectFactory(number=2, name="Mobile App")
    page = open_as(e2e_org.dev1)
    page.goto(week_url(THIS_WEEK))
    total = page.locator("#entries [data-role=week-total]")
    add_row(page, "Project work", "I-001 Customer Portal")  # the wrong project
    panel = open_cell(page, PORTAL, MONDAY)
    panel.get_by_label("Start").fill("09:00")
    panel.get_by_label("End").fill("12:00")
    panel.get_by_label("Reason").fill("Mobile login")
    panel.get_by_role("button", name="Done").click()
    expect(total).to_have_text("3.00")

    panel = menu_item(page, "I-001 Customer Portal", "Change row")
    expect(panel.get_by_label("Category")).to_have_value("PROJECT")
    expect(panel.get_by_label("Category")).to_be_focused()
    pick_project(panel, "I-002 Mobile App")
    panel.get_by_role("button", name="Change row").click()
    expect(page.locator("dialog[open]")).to_have_count(0)
    mobile = "I-002 Mobile App · DEV Development"
    expect(cell(page, mobile, MONDAY)).to_have_text("3.00")
    expect(page.locator('#entries tr[data-row-key^="PROJECT:"]')).to_have_count(1)
    expect(page.locator("[data-week-grid]").get_by_role("status")).to_have_text(
        f"Moved 1 time slot to {mobile}. Save to keep this change."
    )
    expect(page.get_by_role("button", name="Row actions for I-002 Mobile App")).to_be_focused()
    expect(total).to_have_text("3.00")

    add_row(page, "Meetings")
    panel = open_cell(page, "Meetings", MONDAY)
    panel.get_by_label("Start").fill("13:00")
    panel.get_by_label("End").fill("14:00")
    panel.get_by_role("button", name="Done").click()
    expect(total).to_have_text("4.00")
    toggle = page.get_by_role("button", name="Row actions for Meetings")
    panel = menu_item(page, "Meetings", "Delete row")
    expect(panel).to_contain_text(
        "Delete Meetings? This removes 1 time slot (1.00 h) from this week."
    )
    page.keyboard.press("Escape")  # nothing deleted; focus back on the menu button
    expect(page.locator("dialog[open]")).to_have_count(0)
    expect(toggle).to_be_focused()
    expect(total).to_have_text("4.00")
    menu_item(page, "Meetings", "Delete row").get_by_role("button", name="Delete row").click()
    expect(page.locator('#entries tr[data-row-key="MEETING:"]')).to_have_count(0)
    expect(total).to_have_text("3.00")
    expect(page.locator("#day-summary")).to_contain_text("3:00")  # the server's summary too

    page.get_by_role("button", name="Save draft").click()
    expect(status_of(page)).to_have_text("Draft")
    saved = TimeEntry.objects.get()
    assert (saved.project.code, saved.start_time, saved.end_time, saved.reason) == (
        "I-002",
        time(9),
        time(12),
        "Mobile login",
    )


@pytest.mark.parametrize(
    "size",
    [{"width": 1280, "height": 800}, {"width": 390, "height": 844}],
    ids=["laptop", "narrow"],
)
def test_row_menus_in_a_real_browser(e2e_org, open_as, size):
    """T-202: E2E ⋮ menus open on top and unclipped at the ⋮ button (last row, scrolled page);
    their items open dialogs by mouse and keyboard, also after re-draws; Esc returns to ⋮."""
    ProjectFactory(number=2, name="Mobile App")
    page = open_as(e2e_org.dev1)
    page.set_viewport_size(size)
    page.goto(week_url(THIS_WEEK))
    add_row(page, "Project work", "I-001 Customer Portal")
    add_row(page, "Meetings")
    add_row(page, "Break time")
    add_row(page, "PTO")  # the last row
    for name in ("I-001 Customer Portal", "Meetings", "Break (unpaid)", "PTO"):
        toggle, menu = row_menu(page, name)
        page.keyboard.press("Escape")  # the menu closes; focus stays on ⋮
        expect(menu).to_have_count(0)
        expect(toggle).to_be_focused()

    def dialog_opens(name, item, heading):
        dialog = menu_item(page, name, item)
        expect(dialog).to_have_count(1)
        expect(dialog.get_by_role("heading")).to_contain_text(heading)
        page.keyboard.press("Escape")
        expect(page.locator("dialog[open]")).to_have_count(0)
        expect(page.get_by_role("button", name=f"Row actions for {name}")).to_be_focused()

    dialog_opens("I-001 Customer Portal", "Change row", "Change project, task or category")
    panel = open_cell(page, PORTAL, MONDAY)  # a cell edit
    panel.get_by_label("Start").fill("09:00")
    panel.get_by_label("End").fill("12:00")
    panel.get_by_role("button", name="Done").click()
    panel = menu_item(page, "I-001 Customer Portal", "Change row")
    pick_project(panel, "I-002 Mobile App")
    panel.get_by_role("button", name="Change row").click()  # re-draw 1
    expect(page.get_by_role("button", name="Row actions for I-002 Mobile App")).to_be_focused()

    panel = open_cell(page, "Meetings", MONDAY)  # another row, after the re-draw
    panel.get_by_label("Start").fill("13:00")
    panel.get_by_label("End").fill("14:00")
    panel.get_by_role("button", name="Done").click()
    dialog_opens("Meetings", "Delete row", "Delete row")
    row_menu(page, "Break (unpaid)")[1].get_by_role("button", name="Delete row").click()  # empty
    expect(page.locator('#entries tr[data-row-key="BREAK:"]')).to_have_count(0)  # re-draw 2
    dialog_opens("PTO", "Change row", "Change project, task or category")
    add_row(page, "Training")  # a row added after the re-draws
    dialog_opens("Training", "Change row", "Change project, task or category")

    toggle = page.get_by_role("button", name="Row actions for I-002 Mobile App")
    for key, steps, heading in (("Enter", 1, "Change project"), (" ", 2, "Delete row")):
        toggle.focus()
        page.keyboard.press(key)  # opens the menu
        expect(page.locator(".row-actions .dropdown-menu.show")).to_have_count(1)
        for _ in range(steps):
            page.keyboard.press("ArrowDown")
        page.keyboard.press(key)  # the focused item
        expect(page.locator("dialog[open] h2")).to_contain_text(heading)
        page.keyboard.press("Escape")
        expect(toggle).to_be_focused()

    last = page.locator("#entries tr.grid-row").last
    last.evaluate("r => scrollBy(0, r.getBoundingClientRect().bottom - innerHeight + 4)")
    toggle, _ = row_menu(page, "Training")  # the last row at the bottom of the window
    page.keyboard.press("Escape")
    page.locator(".grid-scroll").evaluate("e => e.scrollLeft = e.scrollWidth")  # days scrolled
    row_menu(page, "Meetings")
    page.keyboard.press("Escape")
    expect(page.locator(".dropdown-menu.show")).to_have_count(0)


def test_tasks_and_charge_codes_in_a_real_browser(e2e_org, open_as):
    """T-236: E2E add a Project work row with a task (only the project's tasks offered), enter
    time, change the task with ⋮, save and submit; the manager sees the charge code (D-152)."""
    mobile = ProjectFactory(number=2, name="Mobile App")
    mobile.tasks.set(mobile.tasks.filter(code__in=["DEV", "TST"]))
    page = open_as(e2e_org.dev1)
    page.goto(week_url(THIS_WEEK))
    page.get_by_role("button", name="+ Add row").click()
    panel = page.locator("dialog[open]")
    panel.get_by_label("Category").select_option(label="Project work")
    expect(panel.get_by_label("Task")).to_be_hidden()  # asked once a project is chosen
    pick_project(panel, "I-002 Mobile App")
    expect(panel.get_by_label("Task").locator("option")).to_have_text(
        ["Choose…", "DEV Development", "TST Testing & QA"]
    )
    panel.get_by_role("button", name="Add row", exact=True).click()
    expect(panel.get_by_role("alert")).to_have_text("Choose a task.")
    panel.get_by_label("Task").select_option(label="DEV Development")
    panel.get_by_role("button", name="Add row", exact=True).click()
    dev = "I-002 Mobile App · DEV Development"
    row = page.locator("#entries tr.grid-row", has_text="I-002 Mobile App")
    expect(row.get_by_title("Charge code")).to_have_text("I-002-DEV")
    panel = open_cell(page, dev, MONDAY)
    panel.get_by_label("Start").fill("09:00")
    panel.get_by_label("End").fill("12:00")
    panel.get_by_label("Reason").fill("Test plan")
    panel.get_by_role("button", name="Done").click()

    panel = menu_item(page, "I-002 Mobile App", "Change row")
    expect(panel.get_by_label("Task")).to_have_value("DEV")
    panel.get_by_label("Task").select_option(label="TST Testing & QA")
    panel.get_by_role("button", name="Change row").click()
    tst = "I-002 Mobile App · TST Testing & QA"
    expect(cell(page, tst, MONDAY)).to_have_text("3.00")
    expect(page.locator("#entries").get_by_title("Charge code")).to_have_text(["I-002-TST"])
    page.get_by_role("button", name="Save draft").click()
    expect(status_of(page)).to_have_text("Draft")
    page.get_by_role("button", name="Submit").click()
    expect(status_of(page)).to_have_text("Submitted")
    entry = TimeEntry.objects.get()
    assert (entry.project.code, entry.task.code, entry.reason) == ("I-002", "TST", "Test plan")

    manager = open_as(e2e_org.manager)
    manager.goto(reverse("approval_detail", args=[THIS_WEEK - timedelta(weeks=1), "DEV1"]))
    expect(manager.get_by_title("Charge code")).to_have_text(["I-002-TST"])
    expect(manager.locator("[data-week-grid]").last).to_contain_text(tst)  # week 2 of the period


@pytest.mark.parametrize(
    "size", [{"width": 1280, "height": 900}, {"width": 390, "height": 844}], ids=["laptop", "phone"]
)
def test_project_search_in_a_real_browser(e2e_org, open_as, size):
    """T-243: E2E the project search box: type "portal", pick I-001 with ↓ + Enter, choose a
    task, add the row, enter time, save; ⋮ Change row: "No matching project", then "i-002";
    Esc closes the list before the dialog; on a laptop and a phone (D-157)."""
    ProjectFactory(number=2, name="Mobile App")
    page = open_as(e2e_org.dev1)
    page.set_viewport_size(size)
    page.goto(week_url(THIS_WEEK))
    page.get_by_role("button", name="+ Add row").click()
    panel = page.locator("dialog[open]")
    panel.get_by_label("Category").select_option(label="Project work")
    box = panel.get_by_role("combobox", name="Project")
    expect(box).to_have_attribute("aria-expanded", "false")
    box.click()  # the empty box lists every active project, by I-code
    expect(panel.get_by_role("listbox").get_by_role("option")).to_have_text(
        ["I-001 Customer Portal", "I-002 Mobile App"]
    )
    expect(box).to_have_attribute("aria-expanded", "true")
    box.fill("portal")
    expect(panel.get_by_role("listbox").get_by_role("option")).to_have_text(
        ["I-001 Customer Portal"]
    )
    expect(panel.locator("[data-role=project-count]")).to_have_text("1 project")  # announced
    box.press("ArrowDown")
    expect(box).to_have_attribute("aria-activedescendant", re.compile(r"add-row-project-list-\d+"))
    box.press("Enter")
    expect(box).to_have_value("I-001 Customer Portal")
    expect(panel.get_by_role("listbox")).to_be_hidden()
    panel.get_by_label("Task").select_option(label="DEV Development")
    panel.get_by_role("button", name="Add row", exact=True).click()
    expect(page.locator("dialog[open]")).to_have_count(0)
    panel = open_cell(page, PORTAL, MONDAY)
    panel.get_by_label("Start").fill("09:00")
    panel.get_by_label("End").fill("12:00")
    panel.get_by_role("button", name="Done").click()
    page.get_by_role("button", name="Save draft").click()
    expect(status_of(page)).to_have_text("Draft")

    page.get_by_role("button", name=f"Row actions for {PORTAL}").click()
    page.locator(".row-actions .dropdown-menu.show").get_by_role(
        "button", name="Change row"
    ).click()
    panel = page.locator("dialog[open]")
    box = panel.get_by_role("combobox", name="Project")
    expect(box).to_have_value("I-001 Customer Portal")  # the row's own project
    box.fill("zzz")
    expect(panel.get_by_role("listbox")).to_contain_text("No matching project")
    expect(panel.locator("[data-role=project-count]")).to_have_text("No matching project")
    box.press("Escape")  # closes the list only
    expect(panel.get_by_role("listbox")).to_be_hidden()
    expect(page.locator("dialog[open]")).to_have_count(1)
    box.fill("i-002")
    option = panel.get_by_role("option", name="I-002 Mobile App")
    expect(panel.get_by_role("listbox").get_by_role("option")).to_have_count(1)
    assert option.bounding_box()["width"] <= size["width"]  # fits the phone
    option.click()
    expect(box).to_have_value("I-002 Mobile App")
    expect(panel.get_by_label("Task")).to_have_value("DEV")
    panel.get_by_role("button", name="Change row").click()
    mobile = "I-002 Mobile App · DEV Development"
    expect(cell(page, mobile, MONDAY)).to_have_text("3.00")
    page.get_by_role("button", name="Save draft").click()
    expect(status_of(page)).to_have_text("Draft")
    assert TimeEntry.objects.get().project.code == "I-002"
    assert page.evaluate("document.documentElement.scrollWidth") <= size["width"]
