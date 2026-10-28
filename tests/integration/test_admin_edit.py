from datetime import date, timedelta
from unittest import mock

import pytest
from axes.models import AccessAttempt
from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from audit.models import AuditLog
from audit.services.log import record
from directory.models import Employee, Team, User
from directory.services import directory_admin
from payroll.models import PayrollWeek
from tests.factories import TEST_PASSWORD, EmployeeFactory, ProjectFactory, UserFactory
from timesheets.models import ChangeRequest, PeriodApproval, Project, Timesheet

PERIOD = date(2026, 9, 27)  # most recent completed period at fixed_now: Sep 27 + Oct 4
TEMP = "Temporary-Pass-2026"


@pytest.fixture(autouse=True)
def company_domain(settings):
    settings.COMPANY_EMAIL_DOMAIN = "@yourcompany.com"


def url(model, view, *args):
    return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_{view}", args=args)


def employee_data(employee, **changes):
    """The admin change form as it is filled in for this employee, plus changes."""
    data = {
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "email": employee.email,
        "job_title": employee.job_title,
        "team": employee.team_id or "",
        "manager": employee.manager_id or "",
        "location": employee.location,
        "hire_date": employee.hire_date.isoformat() if employee.hire_date else "",
        "expected_weekly_hours": employee.expected_weekly_minutes / 60,
        "is_admin": employee.is_admin,
        "is_payroll": employee.is_payroll,
        "_save": "Save",
        **changes,
    }
    for flag in ("is_admin", "is_payroll"):  # unchecked boxes are not sent at all
        if data[flag]:
            data[flag] = "on"
        else:
            del data[flag]
    return data


def change(client, employee, **changes):
    return client.post(url(Employee, "change", employee.pk), employee_data(employee, **changes))


def form_errors(response):
    return response.context["adminform"].form.errors


def rows(entity_type="Employee", action=None):
    found = AuditLog.objects.filter(entity_type=entity_type).order_by("pk")
    return list(found.filter(action=action) if action else found)


def act(client, action, *employees, **extra):
    return client.post(
        url(Employee, "changelist"),
        {"action": action, "_selected_action": [e.pk for e in employees], **extra},
    )


def refreshed(employee):
    return Employee.objects.get(pk=employee.pk)


def test_employee_edit_is_audited(org, login_as):
    """T-133: an admin edit saves and writes one UPDATE row with only the changed fields."""
    client = login_as(org.hr)
    other = org.ops_manager.team
    response = change(
        client,
        org.dev1,
        first_name="Jon",
        team=other.pk,
        manager=org.ops_manager.pk,
        expected_weekly_hours="30",
        is_payroll=True,
    )
    assert response.status_code == 302
    dev1 = refreshed(org.dev1)
    assert (dev1.first_name, dev1.team, dev1.manager, dev1.expected_weekly_minutes) == (
        "Jon",
        other,
        org.ops_manager,
        1800,
    )
    [row] = rows("Employee", "UPDATE")
    assert row.actor == org.hr and row.entity_id == "DEV1"
    assert row.before == {
        "first_name": "John",
        "team": org.dev1.team.name,
        "manager_code": "MANAGER",
        "is_payroll": False,
        "expected_weekly_minutes": 2400,
    }
    assert row.after["manager_code"] == "OPSMGR" and row.after["expected_weekly_minutes"] == 1800

    change(client, dev1)  # nothing changed → nothing written
    assert len(rows("Employee", "UPDATE")) == 1

    dev1.first_name = "Johnny"
    with mock.patch("directory.services.directory_admin.record", side_effect=RuntimeError):
        with pytest.raises(RuntimeError):
            directory_admin.save_employee(org.hr, dev1)
    assert refreshed(org.dev1).first_name == "Jon"  # the save rolled back with the audit row


def test_add_and_edit_teams_projects_and_employees(org, login_as):
    """T-134: adding and editing teams, projects and employees writes audit rows (D-88)."""
    client = login_as(org.hr)
    client.post(url(Team, "add"), {"name": "Data", "department": "Technology", "_save": "Save"})
    team = Team.objects.get(name="Data")
    client.post(url(Team, "change", team.pk), {"name": "Data", "department": "Analytics"})
    assert [(r.action, r.entity_id, r.actor) for r in rows("Team")] == [
        ("CREATE", "Data", org.hr),
        ("UPDATE", "Data", org.hr),
    ]
    assert rows("Team")[1].after == {"department": "Analytics"}

    client.post(url(Project, "add"), {"name": "Pilot", "active": "on"})  # the app's I-code
    project = Project.objects.get(code="I-001")
    client.post(url(Project, "change", project.pk), {"code": "I-999", "name": "Pilot 2"})
    project.refresh_from_db()
    assert (project.code, project.name, project.active) == ("I-001", "Pilot 2", False)
    assert [(r.action, r.before, r.after) for r in rows("Project")] == [
        ("CREATE", None, {"code": "I-001", "name": "Pilot", "active": True}),
        ("UPDATE", {"name": "Pilot", "active": True}, {"name": "Pilot 2", "active": False}),
    ]

    new = EmployeeFactory.build(employee_code="new-1", email="New.Person@YourCompany.com")
    response = client.post(
        url(Employee, "add"), employee_data(new, team=team.pk, employee_code="new-1")
    )
    assert response.status_code == 302
    created = Employee.objects.get(employee_code="NEW-1")
    assert created.email == "new.person@yourcompany.com" and created.status == "ACTIVE"
    [row] = rows("Employee", "CREATE")
    assert row.actor == org.hr and row.after["team"] == "Data"

    assert 'name="employee_code"' in client.get(url(Employee, "add")).content.decode()
    page = client.get(url(Employee, "change", created.pk)).content.decode()
    assert 'id="reset-password"' in page and 'name="employee_code"' not in page
    assert 'name="status"' not in page and 'name="end_date"' not in page  # actions only
    assert 'name="expected_weekly_hours" value="40"' in page  # minutes shown as hours
    listing = client.get(url(Employee, "changelist")).content.decode()
    assert 'id="import-csv"' in listing and 'id="export-csv"' in listing
    assert "Check file" in client.get(reverse("admin:directory_employee_import")).content.decode()


@pytest.mark.django_db(databases=["default", "payroll"])
def test_workflow_records_are_read_only(org, make_week, login_as):
    """T-135: timesheets, approvals, requests, audit, payroll, users and lockouts are read-only."""
    sheet = make_week(org.dev1, PERIOD)
    request_ = ChangeRequest.objects.create(timesheet=sheet, requester=org.dev1, reason="x")
    approval = PeriodApproval.objects.create(employee=org.dev1, period_start=PERIOD)
    audit = record("CREATE", "Timesheet", sheet.pk, system_actor="seed_demo")
    attempt = AccessAttempt.objects.create(username="x@yourcompany.com", failures_since_start=1)
    user = UserFactory(employee=org.dev2)
    client = login_as(org.hr)
    for obj in (sheet, request_, approval, audit, attempt, user):
        model = type(obj)
        assert client.get(url(model, "changelist")).status_code == 200
        assert client.get(url(model, "add")).status_code == 403
        assert client.post(url(model, "change", obj.pk), {}).status_code == 403
    assert client.get(url(PayrollWeek, "changelist")).status_code == 200
    assert client.get(url(PayrollWeek, "add")).status_code == 403
    assert not admin.site.is_registered(Group)
    assert client.get("/admin/auth/group/").status_code == 404


@pytest.mark.django_db(databases=["default", "payroll"])
def test_nothing_can_be_deleted(org, rf, login_as):
    """T-136: no model allows delete and the "delete selected" action is never offered."""
    request = rf.get("/admin/")
    request.user = User.objects.get(pk=UserFactory(employee=org.ceo).pk)
    for model, model_admin in admin.site._registry.items():
        assert not model_admin.has_delete_permission(request), model
    client = login_as(org.hr)
    project = ProjectFactory()
    for obj in (org.dev1, org.dev1.team, project):
        assert client.get(url(type(obj), "delete", obj.pk)).status_code == 403
        assert client.post(url(type(obj), "delete", obj.pk), {"post": "yes"}).status_code == 403
        page = client.get(url(type(obj), "changelist"))
        form = page.context["action_form"]  # None when a model has no actions at all
        actions = [name for name, _ in form.fields["action"].choices] if form else []
        assert "delete_selected" not in actions
    assert Employee.objects.filter(pk=org.dev1.pk).exists()


@pytest.mark.django_db(databases=["default", "payroll"])
def test_deactivate(org, make_week, login_as, django_capture_on_commit_callbacks):
    """T-137: deactivate sets INACTIVE + end date, ends the session, keeps approve and pay."""
    make_week(org.dev1, PERIOD)
    make_week(org.dev1, PERIOD + timedelta(weeks=1))
    dev1_browser = Client()
    dev1_browser.force_login(UserFactory(employee=org.dev1))
    assert dev1_browser.get(reverse("home")).status_code == 200

    hr = login_as(org.hr)
    page = act(hr, "deactivate", org.dev1)
    assert page.status_code == 200 and 'value="2026-10-21"' in page.content.decode()  # today
    act(hr, "deactivate", org.dev1, apply="Deactivate", end_date="2026-10-16")
    dev1 = refreshed(org.dev1)
    assert (dev1.status, dev1.end_date) == ("INACTIVE", date(2026, 10, 16))
    assert dev1.account.is_active is False
    [row] = rows("Employee", "UPDATE")
    assert row.actor == org.hr
    assert row.after == {"status": "INACTIVE", "end_date": "2026-10-16"}

    response = dev1_browser.get(reverse("home"))
    assert response.status_code == 302 and response.url.startswith(reverse("login"))
    assert Timesheet.objects.filter(employee=dev1).count() == 2  # history kept

    manager = Client()
    manager.force_login(UserFactory(employee=org.manager))
    with django_capture_on_commit_callbacks(execute=True):
        manager.post(reverse("approval_detail", args=[PERIOD, "DEV1"]), {"action": "approve"})
    assert PeriodApproval.objects.get(employee=dev1, period_start=PERIOD).status == "APPROVED"
    assert PayrollWeek.objects.filter(employee_code="DEV1").count() == 2  # paid as usual


def test_deactivate_and_reactivate_rules(org, make_week, login_as, fixed_now):
    """T-138: refusals leave everyone unchanged; reactivate clears the end date (D-90)."""
    make_week(org.dev2, date(2026, 10, 11))  # entries Mon 12 – Fri 16 Oct
    today = date(2026, 10, 21)

    def refused(actor, people, end_date=today):
        with pytest.raises(ValidationError) as exc:
            directory_admin.deactivate(actor, people, end_date)
        return " ".join(exc.value.messages)

    assert "deactivate yourself" in refused(org.hr, [org.hr])
    assert "still manages 2 active people" in refused(org.hr, [org.manager])
    assert "in the future" in refused(org.hr, [org.dev1], today + timedelta(days=1))
    assert "before their hire date" in refused(org.hr, [org.dev1], date(2023, 1, 2))
    assert "time entries up to Oct 16, 2026" in refused(org.hr, [org.dev2], date(2026, 10, 14))
    Employee.objects.filter(pk=org.ceo.pk).update(is_admin=False)
    assert "At least one active admin" in refused(org.ceo, [org.hr])
    assert not Employee.objects.exclude(status="ACTIVE").exists()
    assert not rows()

    client = login_as(org.hr)
    refusal = act(client, "deactivate", org.hr, apply="1", end_date="2026-10-21")
    shown = client.get(refusal.url).content.decode()
    assert "You cannot deactivate yourself." in shown and "Nobody was deactivated." in shown
    # a manager together with all their reports is fine
    act(client, "deactivate", org.manager, org.dev1, org.dev2, apply="1", end_date="2026-10-21")
    assert set(
        Employee.objects.filter(status="INACTIVE").values_list("employee_code", flat=True)
    ) == {
        "MANAGER",
        "DEV1",
        "DEV2",
    }
    act(client, "reactivate", org.dev1)
    dev1 = refreshed(org.dev1)
    assert (dev1.status, dev1.end_date, dev1.hire_date) == ("ACTIVE", None, org.dev1.hire_date)
    assert rows("Employee", "UPDATE")[-1].after == {"status": "ACTIVE", "end_date": None}
    again = act(client, "reactivate", org.dev1)
    assert "is already active" in client.get(again.url).content.decode()
    assert len(rows("Employee", "UPDATE")) == 4  # 3 deactivations + 1 reactivation


def test_email_and_flag_sync(org, login_as):
    """T-139: email changes reach the login account lower-cased; flags follow (D-13, D-20)."""
    UserFactory(employee=org.dev1)
    UserFactory(employee=org.dev2)
    client = login_as(org.hr)
    change(client, org.dev1, email="  John.Kim@YourCompany.COM ")
    dev1 = refreshed(org.dev1)
    assert dev1.email == dev1.account.email == "john.kim@yourcompany.com"

    wrong = change(client, dev1, email="john@gmail.com")
    assert "not a company email address" in str(form_errors(wrong)["email"])
    taken = change(client, dev1, email="DEV2@yourcompany.com")
    assert "already exists" in str(form_errors(taken)["email"])  # any case: lower-cased first
    assert refreshed(org.dev1).email == "john.kim@yourcompany.com"

    change(client, dev1, is_admin=True)
    account = User.objects.get(employee=dev1)
    assert (account.is_staff, account.is_superuser) == (True, True)
    change(client, refreshed(dev1), is_admin=False)
    account.refresh_from_db()
    assert (account.is_staff, account.is_superuser) == (False, False)


def test_safety_rules(org, login_as):
    """T-140: no self-demotion, one active admin remains, no own manager, no loops (D-89)."""
    client = login_as(org.hr)
    errors = form_errors(change(client, org.hr, is_admin=False))
    assert "cannot remove your own admin flag" in str(errors["is_admin"])
    errors = form_errors(change(client, org.dev1, manager=org.dev1.pk))
    assert "cannot be their own manager" in str(errors["manager"])
    errors = form_errors(change(client, org.director, manager=org.dev1.pk))
    assert "loop" in str(errors["manager"])
    leaver = EmployeeFactory(status="INACTIVE", employee_code="LEFT")
    errors = form_errors(change(client, org.dev1, manager=leaver.pk))
    assert "inactive" in str(errors["manager"])
    assert refreshed(org.director).manager == org.ceo and refreshed(org.hr).is_admin

    Employee.objects.filter(pk=org.ceo.pk).update(is_admin=False)  # HR is the last admin
    org.hr.is_admin = False
    assert "At least one active admin" in str(directory_admin.check_employee(org.dev1, org.hr))
    change(client, org.ceo, is_admin=False)  # nothing to remove: fine
    assert not rows("Employee", "UPDATE")


def test_password_reset(org, login_as, client):
    """T-141: HR reset: rules apply, no password in the audit, forced change, lockout cleared."""
    dev1_user = UserFactory(employee=org.dev1)
    old_session = Client()
    old_session.force_login(dev1_user)
    AccessAttempt.objects.create(username=dev1_user.email, failures_since_start=5)
    hr = login_as(org.hr)
    reset_url = reverse("admin:directory_employee_reset_password", args=[org.dev1.pk])

    weak = hr.post(reset_url, {"new_password1": "short", "new_password2": "short"})
    assert "too short" in weak.content.decode()
    response = hr.post(reset_url, {"new_password1": TEMP, "new_password2": TEMP})
    assert response.status_code == 302
    dev1_user.refresh_from_db()
    assert dev1_user.password.startswith("argon2") and dev1_user.must_change_password
    [row] = rows("User")
    assert row.actor == org.hr and row.before is None
    assert row.after == {
        "changed": ["password"],
        "must_change_password": True,
        "lockout_cleared": 1,
    }
    assert TEMP not in str(row.after) and dev1_user.password not in str(row.after)
    assert not AccessAttempt.objects.filter(username=dev1_user.email).exists()
    assert old_session.get(reverse("home")).status_code == 302  # their open session ended

    client.logout()
    client.post(reverse("login"), {"username": dev1_user.email, "password": TEMP})
    for page in (reverse("home"), reverse("timesheets")):
        assert client.get(page).url == reverse("profile")
    assert client.get(reverse("profile")).status_code == 200
    client.post(
        reverse("profile"),
        {
            "old_password": TEMP,
            "new_password1": "Brand-New-Pass-77",
            "new_password2": "Brand-New-Pass-77",
        },
    )
    dev1_user.refresh_from_db()
    assert dev1_user.must_change_password is False
    assert client.get(reverse("home")).status_code == 200

    hr = login_as(org.hr)
    own = hr.get(reverse("admin:directory_employee_reset_password", args=[org.hr.pk]))
    assert (
        'id="reset-refused"' in own.content.decode()
        and "<form" not in own.content.decode().split('id="content"')[1]
    )
    with pytest.raises(ValidationError):
        directory_admin.reset_password(org.hr, org.hr, TEMP)
    no_account = hr.get(reverse("admin:directory_employee_reset_password", args=[org.ops1.pk]))
    assert "has no account yet" in no_account.content.decode()
    assert hr.get(reverse("admin:password_change")).url == reverse("profile")


def test_only_directory_admins_reach_admin(org, login_as, client):
    """T-144: employees, managers and payroll users get 403; anonymous users go to /login/."""
    pages = [
        reverse("admin:index"),
        url(Employee, "changelist"),
        url(Employee, "change", org.dev1.pk),
        reverse("admin:directory_employee_import"),
        reverse("admin:directory_employee_export"),
        reverse("admin:directory_employee_reset_password", args=[org.dev1.pk]),
        url(Timesheet, "changelist"),
    ]
    anonymous = client.get(pages[1])
    assert anonymous.status_code == 302 and anonymous.url.startswith(reverse("login"))
    for person in (org.dev1, org.manager, org.payroll, org.finance):
        browser = login_as(person)
        for page in pages:
            assert browser.get(page).status_code == 403, (person, page)
        assert (
            act(browser, "deactivate", org.dev2, apply="1", end_date="2026-10-21").status_code
            == 403
        )
    assert refreshed(org.dev2).status == "ACTIVE" and not rows()

    hr_browser = Client()
    hr_browser.force_login(UserFactory(employee=org.hr))
    assert hr_browser.get(pages[0]).status_code == 200
    act(login_as(org.ceo), "deactivate", org.hr, apply="1", end_date="2026-10-21")
    assert hr_browser.get(pages[0]).status_code == 302  # an inactive admin is logged out


def test_search_and_filters(org, login_as):
    """T-145: employee search and filters; audit log filters by action, actor, entity, date."""
    EmployeeFactory(status="INACTIVE", employee_code="LEFT", manager=org.manager)
    client = login_as(org.hr)

    def listed(**params):
        page = client.get(url(Employee, "changelist"), params)
        return {e.employee_code for e in page.context["cl"].result_list}

    assert listed(q="Kim") == {"DEV1"}
    assert listed(manager__id__exact=org.manager.pk) == {"DEV1", "DEV2", "LEFT"}
    assert listed(is_payroll__exact=1) == {"FINANCE", "PAYROLL"}
    assert listed(status__exact="INACTIVE") == {"LEFT"}
    assert listed(team__department=org.dev1.team.department) >= {"DEV1", "DEV2"}
    assert listed(q=org.manager.last_name) >= {"DEV1", "DEV2", "MANAGER"}

    record("EXPORT", "Employee", "csv", actor=org.hr)
    record("CREATE", "Team", "Data", actor=org.ceo)
    record("SYNC", "PayrollWeek", "x", system_actor="sync_payroll")

    def audit(**params):
        page = client.get(url(AuditLog, "changelist"), params)
        return {(r.action, r.entity_type) for r in page.context["cl"].result_list}

    assert audit(action__exact="EXPORT") == {("EXPORT", "Employee")}
    assert audit(actor__id__exact=org.ceo.pk) == {("CREATE", "Team")}
    assert audit(entity_type="PayrollWeek") == {("SYNC", "PayrollWeek")}
    assert (
        len(
            audit(
                created_at__gte="2000-01-01T00:00:00+00:00",
                created_at__lt="2100-01-01T00:00:00+00:00",
            )
        )
        == 3
    )
    assert (
        audit(
            created_at__gte="2000-01-01T00:00:00+00:00", created_at__lt="2000-01-02T00:00:00+00:00"
        )
        == set()
    )
    assert (
        client.get(url(Timesheet, "changelist"), {"status__exact": "SUBMITTED"}).status_code == 200
    )
    page = client.get(url(Team, "changelist"), {"q": org.dev1.team.name})
    assert [t.name for t in page.context["cl"].result_list] == [org.dev1.team.name]


def test_login_with_reset_password_needs_request(org):
    """Helper check: the temporary password works with the normal password check."""
    user = UserFactory(employee=org.dev1)
    directory_admin.reset_password(org.hr, org.dev1, TEMP)
    user.refresh_from_db()
    assert user.check_password(TEMP) and not user.check_password(TEST_PASSWORD)
