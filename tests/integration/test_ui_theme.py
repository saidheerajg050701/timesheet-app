import re
from datetime import date
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from payroll.models import PayrollWeek
from timesheets.models import ChangeRequest, PeriodApproval, Timesheet
from timesheets.templatetags.timesheet_tags import TONES, status_label, status_tone

THEME = Path(settings.BASE_DIR) / "static" / "css" / "theme.css"
TEMPLATES = Path(settings.BASE_DIR) / "templates"


def tokens():
    """{name: value} for every --ts-* custom property in theme.css."""
    return dict(re.findall(r"(--ts-[\w-]+):\s*([^;]+);", THEME.read_text()))


def luminance(hex_colour):
    channels = [int(hex_colour.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first, second):
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.django_db
def test_theme_stylesheet_is_loaded_and_served(settings, user):
    """T-157: every page links css/theme.css after Bootstrap; it is served with DEBUG off."""
    settings.DEBUG = False
    browser = Client()
    login_page = browser.get(reverse("login")).content.decode()
    browser.force_login(user)
    for html in (login_page, browser.get(reverse("home")).content.decode()):
        bootstrap = html.index("/static/vendor/bootstrap/bootstrap.min.css")
        assert html.index('href="/static/css/theme.css"') > bootstrap
    css = Client().get("/static/css/theme.css")
    assert css.status_code == 200 and css["Content-Type"].startswith("text/css")
    assert b"--ts-accent:" in b"".join(css.streaming_content)


@pytest.mark.django_db
def test_one_status_badge_component(org, login_as, make_week, fixed_now):
    """T-158: every status and flag has a tone with CSS; pages use only the shared component."""
    codes = {
        *Timesheet.Status.values,
        *PeriodApproval.Status.values,
        *ChangeRequest.Status.values,
        *PayrollWeek.Status.values,
        "NOT_STARTED", "OUTSIDE_EMPLOYMENT", "IN_PROGRESS",
        "LATE", "MISSED", "OVERTIME", "MISSING", "CHANGE_REQUESTED", "READ_ONLY",
    }  # fmt: skip
    css = THEME.read_text()
    for code in codes:
        assert code in TONES, code
        assert f".tone-{status_tone(code)} {{" in css, code
        assert status_label(code) and status_label(code) == status_label(code).strip()
    assert (status_label("IN_PROGRESS"), status_label("PAID")) == ("In progress", "Paid")

    legacy = [
        str(path.relative_to(TEMPLATES))
        for path in TEMPLATES.rglob("*.html")
        if "admin" not in path.parts and re.search(r"text-bg-|\|status_badge\b", path.read_text())
    ]
    assert legacy == []

    make_week(org.dev1, date(2026, 10, 11))
    html = login_as(org.dev1).get(reverse("timesheet_week", args=[date(2026, 10, 11)]))
    page = html.content.decode()
    assert 'class="badge status-badge tone-submitted" id="week-status">Submitted<' in page


def test_theme_contrast_meets_wcag_aa():
    """T-159: badge tones, body and muted text, and the accent button reach 4.5:1 (WCAG AA)."""
    t = tokens()
    tones = {name[len("--ts-tone-") : -3] for name in t if name.startswith("--ts-tone-")}
    assert tones == {
        "neutral",
        "draft",
        "submitted",
        "approved",
        "danger",
        "reopened",
        "warning",
        "info",
    }
    pairs = [(t[f"--ts-tone-{tone}-fg"], t[f"--ts-tone-{tone}-bg"]) for tone in tones]
    pairs += [
        (t["--ts-text"], t["--ts-bg"]),
        (t["--ts-text-muted"], t["--ts-bg"]),
        (t["--ts-text-muted"], t["--ts-surface"]),
        ("#ffffff", t["--ts-accent"]),
        ("#ffffff", t["--ts-success"]),
        (t["--ts-accent-soft-text"], t["--ts-accent-soft"]),  # active menu item
        (t["--ts-danger"], t["--ts-surface"]),
    ]
    for fg, bg in pairs:
        assert contrast(fg, bg) >= 4.5, (fg, bg, round(contrast(fg, bg), 2))
