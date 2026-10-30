"""Shared helpers of the browser tests (D-94): addresses, grid cells and dialogs, the project
search box, row menus and report downloads."""

import re
from datetime import timedelta

from django.urls import reverse
from playwright.sync_api import expect

from tests.e2e.conftest import PERIOD, THIS_WEEK

NEW_PASSWORD = "Brand-New-Pass-2026"
WEEK2 = PERIOD + timedelta(weeks=1)

MONDAY = THIS_WEEK + timedelta(days=1)  # weeks start on Sunday (D-111)


def week_url(week):
    return reverse("timesheet_week", args=[week])


def status_of(page):
    return page.locator("#week-status")


PORTAL = "I-001 Customer Portal · DEV Development"

BREAK = "Break (unpaid)"


def cell(page, row, day):
    """A grid cell's button, e.g. cell(page, PORTAL, date(2026, 10, 19)) (D-106)."""
    name = re.escape(f"{row}, {day:%a %b %-d}:").replace("/", r"\/")  # Playwright: /…/ regex
    return page.get_by_role("button", name=re.compile(f"^{name}"))


def open_cell(page, row, day):
    cell(page, row, day).click()
    panel = page.locator("dialog[open]")
    expect(panel).to_be_visible()
    return panel


def pick_project(panel, project, typed=None):
    """Search the dialog's project box (its I-code unless told otherwise) and click the
    project, e.g. pick_project(panel, "I-002 Mobile App") (D-157)."""
    panel.get_by_label("Project", exact=True).fill(typed or project.split()[0])
    panel.get_by_role("option", name=project).click()


def add_row(page, category, project=None, task="DEV Development"):
    """+ Add row; project work also chooses the project, then one of its tasks (D-152)."""
    page.get_by_role("button", name="+ Add row").click()
    panel = page.locator("dialog[open]")
    panel.get_by_label("Category").select_option(label=category)
    if project:
        pick_project(panel, project)
        panel.get_by_label("Task").select_option(label=task)
    panel.get_by_role("button", name="Add row", exact=True).click()


# Is the element fully inside the window and the top element at its left, middle and right
# (not covered by another row, not clipped by the scrolling table or the card)?

ON_TOP = """(el) => {
  const r = el.getBoundingClientRect();
  const inside = r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight;
  const y = r.top + r.height / 2;
  return inside && [r.left + 4, r.left + r.width / 2, r.right - 4].every((x) => {
    const hit = document.elementFromPoint(x, y);
    return hit === el || el.contains(hit);
  });
}"""

MENU_ITEMS = ("Change row", "Delete row")


def row_menu(page, name):
    """Open a row's ⋮ menu with a real click (D-129): both items visible, on top of everything,
    and the menu starts at the ⋮ button. Returns (toggle, menu)."""
    toggle = page.get_by_role("button", name=f"Row actions for {name}")
    label = page.locator("#entries tr.grid-row", has=toggle).locator(".grid-label-text")
    button, text = toggle.bounding_box(), label.bounding_box()
    assert button["x"] >= text["x"] + text["width"] - 1, name  # right of the name …
    assert button["y"] < text["y"] + text["height"], name  # … on its first line, not below
    toggle.click()
    menu = page.locator(".row-actions .dropdown-menu.show")
    expect(menu).to_have_count(1)
    for item in MENU_ITEMS:
        button = menu.get_by_role("button", name=item)
        expect(button).to_be_visible()
        assert button.evaluate(ON_TOP), f"{name}: {item!r} is covered, clipped or off screen"
    assert abs(menu.bounding_box()["x"] - toggle.bounding_box()["x"]) <= 2, name  # aligned
    return toggle, menu


def menu_item(page, name, item):
    """Open the row's menu and click one of its items, both for real; returns the dialog."""
    _, menu = row_menu(page, name)
    menu.get_by_role("button", name=item).click()
    return page.locator("dialog[open]")


REPORT_FILES = "2026-09-27_to_2026-10-10"  # the last pay period at the e2e clock


def downloads(page, prefix):
    """Download the report's Excel and CSV; returns their file names."""
    names = []
    for link in ("Download Excel", "Download CSV"):
        with page.expect_download() as download:
            page.get_by_role("link", name=link).click()
        names.append(download.value.suggested_filename)
    assert names == [f"{prefix}{REPORT_FILES}.xlsx", f"{prefix}{REPORT_FILES}.csv"]
    return names


def choose_report_project(page, typed, project):
    box = page.get_by_role("combobox", name="Project")
    box.fill(typed)
    page.get_by_role("listbox").get_by_role("option", name=project).click()
    expect(page.locator("[data-role=project-chips]")).to_contain_text(project)
    page.get_by_role("button", name="Apply").click()
