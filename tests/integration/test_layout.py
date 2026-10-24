import json

import pytest
from django.urls import reverse

from audit.models import AuditLog
from directory.models import User
from directory.services.permissions import can_approve, can_view
from tests.factories import TEST_PASSWORD

NEW_PASSWORD = "Fresh-Password-2026"
PAGES = ("home", "timesheets", "requests", "team", "approvals", "payroll", "profile")


def status_of(client, name, *args):
    return client.get(reverse(name, args=args)).status_code


def menu_links(html):
    return {name for name in PAGES if f'href="{reverse(name)}"' in html} | (
        {"admin"} if f'href="{reverse("admin:index")}"' in html else set()
    )


def test_employee_is_refused_manager_and_payroll_pages(org, login_as):
    """T-26: an employee gets 403 on /team/, another person's page, approvals and payroll."""
    client = login_as(org.dev1)
    for name in ("team", "approvals", "payroll"):
        assert status_of(client, name) == 403, name
    assert status_of(client, "team_member", org.dev2.employee_code) == 403
    assert status_of(client, "team_member", org.dev1.employee_code) == 403  # /team/ is for managers
    for name in ("home", "timesheets", "requests", "profile"):
        assert status_of(client, name) == 200, name


@pytest.mark.django_db(databases=["default", "payroll"])  # /payroll/ reads payroll
def test_payroll_flag_adds_only_payroll_pages(org, login_as):
    """T-62: a payroll user with no reports reaches /payroll/ and nothing else extra (D-12)."""
    client = login_as(org.payroll)
    assert status_of(client, "payroll") == 200
    for name in ("team", "approvals"):
        assert status_of(client, name) == 403, name
    for other in (org.dev1, org.finance, org.ceo):
        assert status_of(client, "team_member", other.employee_code) == 403
        assert not can_view(org.payroll, other)


@pytest.mark.django_db(databases=["default", "payroll"])  # /payroll/ reads payroll
def test_payroll_user_who_manages_gets_manager_rights_for_own_tree(org, login_as):
    """T-63: a payroll user who is also a manager gets manager rights for their own tree only."""
    client = login_as(org.finance)
    for name in ("payroll", "team", "approvals"):
        assert status_of(client, name) == 200, name
    assert status_of(client, "team_member", org.payroll.employee_code) == 200
    assert can_view(org.finance, org.payroll) and can_approve(org.finance, org.payroll)
    assert status_of(client, "team_member", org.dev1.employee_code) == 403
    assert not can_view(org.finance, org.dev1) and not can_approve(org.finance, org.dev1)


def test_menu_and_header_follow_roles(org, login_as):
    """T-64: menu per role; header shows name, Employee ID, job title and team (FR-4)."""
    always = {"home", "timesheets", "requests", "profile"}
    expected = {
        org.dev1: always,
        org.manager: always | {"team", "approvals"},
        org.payroll: always | {"payroll"},
        org.finance: always | {"team", "approvals", "payroll"},
        org.hr: always | {"team", "approvals", "payroll", "admin"},
    }
    for employee, links in expected.items():
        html = login_as(employee).get("/").content.decode()
        assert menu_links(html) == links, employee.employee_code

    html = login_as(org.dev1).get("/").content.decode()
    header = html.split('id="who-am-i"')[1].split("</a>")[0]
    for text in ("John Kim", "DEV1", org.dev1.job_title, "Platform"):
        assert text in header


def test_profile_shows_directory_details_read_only(org, login_as):
    """T-65: /profile/ shows the directory details read-only (FR-4)."""
    response = login_as(org.dev1).get(reverse("profile"))
    html = response.content.decode()
    details = html.split('id="directory-details"')[1].split("</dl>")[0]
    for text in (
        "John Kim",
        "DEV1",
        "dev1@yourcompany.com",
        org.dev1.job_title,
        "Platform",
        "Technology",
        f"{org.manager.first_name} {org.manager.last_name} (MANAGER)",
        "Dallas",
        "Jan 8, 2024",
    ):
        assert text in details, text
    form_fields = set(response.context["form"].fields)
    assert form_fields == {"old_password", "new_password1", "new_password2"}  # nothing editable


def test_password_change_keeps_session_and_audits_without_password_data(org, login_as):
    """T-66: password change: <12 refused; success keeps login; audit row has no password data."""
    client = login_as(org.dev1)
    user = User.objects.get(employee=org.dev1)
    url = reverse("profile")

    short = {
        "old_password": TEST_PASSWORD,
        "new_password1": "Short-Pw-1",
        "new_password2": "Short-Pw-1",
    }
    response = client.post(url, short)
    assert response.status_code == 200 and "at least 12 characters" in response.content.decode()
    wrong = {"old_password": "nope", "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}
    assert client.post(url, wrong).status_code == 200
    user.refresh_from_db()
    assert user.check_password(TEST_PASSWORD) and not AuditLog.objects.exists()

    ok = {
        "old_password": TEST_PASSWORD,
        "new_password1": NEW_PASSWORD,
        "new_password2": NEW_PASSWORD,
    }
    response = client.post(url, ok)
    assert response.status_code == 302 and response.url == url
    page = client.get(url)  # still logged in
    assert page.status_code == 200 and "Your password was changed." in page.content.decode()
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD) and not user.check_password(TEST_PASSWORD)
    assert user.password.startswith("argon2")

    row = AuditLog.objects.get()
    assert (row.action, row.entity_type, row.actor) == ("UPDATE", "User", org.dev1)
    stored = json.dumps([row.before, row.after])
    for secret in (TEST_PASSWORD, NEW_PASSWORD, user.password, *user.password.split("$")[-2:]):
        assert secret not in stored


@pytest.mark.django_db
def test_new_password_works_at_login(client, user):
    """Helper check: after changing the password, only the new one logs in."""
    client.force_login(user)
    data = {
        "old_password": TEST_PASSWORD,
        "new_password1": NEW_PASSWORD,
        "new_password2": NEW_PASSWORD,
    }
    client.post(reverse("profile"), data)
    client.post(reverse("logout"))
    login = reverse("login")
    assert (
        client.post(login, {"username": user.email, "password": TEST_PASSWORD}).status_code == 200
    )
    assert client.post(login, {"username": user.email, "password": NEW_PASSWORD}).status_code == 302


def test_team_member_page_rules(org, login_as):
    """Helper check: managers see their own tree only; admins anyone; unknown code is 404."""
    client = login_as(org.director)
    assert status_of(client, "team_member", org.dev1.employee_code) == 200  # indirect report
    assert status_of(client, "team_member", org.ops1.employee_code) == 403
    assert status_of(client, "team_member", "NOPE-0000") == 404
    client = login_as(org.hr)
    assert status_of(client, "team_member", org.ops1.employee_code) == 200
    assert 'id="team-filters"' in client.get(reverse("team")).content.decode()  # the real page
