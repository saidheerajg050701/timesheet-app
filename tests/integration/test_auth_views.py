from datetime import timedelta

import pytest
import time_machine
from django.db import connections
from django.urls import reverse

from audit.models import AuditLog
from directory.models import Employee, User
from directory.services.signup import check_signup_eligibility, create_account
from tests.factories import TEST_PASSWORD, EmployeeFactory, UserFactory

NEW_PASSWORD = "Long-Enough-Pass-1"


def log_in(client, email, password, **extra):
    return client.post(reverse("login"), {"username": email, "password": password, **extra})


def sign_up(client, email, password=NEW_PASSWORD, confirm=None):
    data = {"email": email, "password1": password, "password2": confirm or password}
    return client.post(reverse("signup"), data)


def logged_in_user_id(client):
    return client.session.get("_auth_user_id")


# --- sign-up (FR-2) ---------------------------------------------------------------------


@pytest.mark.django_db
def test_signup_creates_account_with_lowercase_email(client):
    """T-05: valid directory email, mixed case + spaces → account created, stored lower-case."""
    employee = EmployeeFactory(email="ravi.kumar@yourcompany.com", first_name="Ravi")
    response = sign_up(client, "  Ravi.Kumar@YourCompany.COM ")
    assert response.status_code == 302 and response.url == reverse("home")

    user = User.objects.get(employee=employee)
    assert user.email == "ravi.kumar@yourcompany.com"
    assert user.password.startswith("argon2") and user.check_password(NEW_PASSWORD)
    assert logged_in_user_id(client) == str(user.pk)
    assert "Welcome, Ravi! Your account is ready." in client.get("/").content.decode()
    audit = AuditLog.objects.get(entity_type="User", action=AuditLog.Action.CREATE)
    assert audit.actor == employee and audit.entity_id == user.email


@pytest.mark.django_db
def test_signup_page_uses_the_agreed_labels(client):
    """Helper check: labels and button match the Phase 12 browser tests (B.11)."""
    html = client.get(reverse("signup")).content.decode()
    assert '<label for="id_email" class="form-label">Email</label>' in html
    assert '<label for="id_password1" class="form-label">Password</label>' in html
    assert '<label for="id_password2" class="form-label">Confirm password</label>' in html
    assert '<button type="submit" class="btn btn-primary w-100">Sign up</button>' in html


@pytest.mark.django_db
def test_signup_refusals_are_shown_and_create_nothing(client):
    """Helper check: refusal messages reach the page; no account is created."""
    EmployeeFactory(email="former@yourcompany.com", status=Employee.Status.INACTIVE)
    existing = UserFactory()
    cases = {
        "nobody@yourcompany.com": "not in the company employee directory",
        "former@yourcompany.com": "not in the company employee directory",
        "dev1@gmail.com": "Use your company email address",
        existing.email: "An account already exists — please log in.",
    }
    for email, text in cases.items():
        response = sign_up(client, email)
        assert response.status_code == 200
        assert text in response.content.decode()
    assert User.objects.count() == 1
    assert logged_in_user_id(client) is None


@pytest.mark.django_db
def test_signup_rejects_mismatched_or_weak_passwords(client, employee):
    """Helper check: passwords must match and pass the validators (FR-2 step 5)."""
    response = sign_up(client, employee.email, NEW_PASSWORD, "Different-Pass-2")
    assert "The two passwords don&#x27;t match." in response.content.decode()
    response = sign_up(client, employee.email, "short")
    assert "at least 12 characters" in response.content.decode()
    response = sign_up(client, employee.email, employee.email)
    assert "too similar" in response.content.decode()
    assert not User.objects.exists()


@pytest.mark.django_db
def test_create_account_race_reports_existing_account(employee):
    """Helper check: if the account appears between check and create, report "already exists"."""
    eligibility = check_signup_eligibility(employee.email)
    user, refused = create_account(eligibility, NEW_PASSWORD)
    assert user and refused is None
    user, refused = create_account(eligibility, NEW_PASSWORD)
    assert user is None and "already exists" in refused.message
    assert User.objects.count() == 1


# --- login (FR-1) -----------------------------------------------------------------------


@pytest.mark.django_db
def test_correct_password_logs_in(client, user):
    """T-09: the correct password logs in (email is case-insensitive)."""
    response = log_in(client, f" {user.email.upper()} ", TEST_PASSWORD)
    assert response.status_code == 302 and response.url == reverse("home")
    assert logged_in_user_id(client) == str(user.pk)

    client.post(reverse("logout"))
    response = log_in(client, user.email, TEST_PASSWORD, next="/admin/")
    assert response.url == "/admin/"


@pytest.mark.django_db
def test_wrong_password_shows_one_generic_error(client, user):
    """Helper check: a wrong password gives the generic error and no session."""
    response = log_in(client, user.email, "Wrong-Password-1")
    assert response.status_code == 200
    assert "Wrong email or password." in response.content.decode()
    assert logged_in_user_id(client) is None


@pytest.mark.django_db
def test_five_wrong_attempts_lock_the_account_for_15_minutes(client, user, fixed_now):
    """T-10: 5 wrong attempts lock the account for 15 minutes."""
    with time_machine.travel(fixed_now, tick=False) as clock:
        for attempt in range(4):  # any capitalisation counts against the same account (D-28)
            email = user.email.upper() if attempt % 2 else user.email
            assert log_in(client, email, f"Wrong-Password-{attempt}").status_code == 200
        assert log_in(client, user.email, "Wrong-Password-4").status_code == 429  # 5th locks

        locked = log_in(client, user.email, TEST_PASSWORD)
        assert locked.status_code == 429
        assert "Too many failed attempts" in locked.content.decode()
        assert logged_in_user_id(client) is None

        clock.move_to(fixed_now + timedelta(minutes=15, seconds=1))
        response = log_in(client, user.email, TEST_PASSWORD)
        assert response.status_code == 302
        assert logged_in_user_id(client) == str(user.pk)


@pytest.mark.django_db
def test_lock_still_holds_just_before_15_minutes(client, user, fixed_now):
    """Helper check: the account is still locked at 14:59."""
    with time_machine.travel(fixed_now, tick=False) as clock:
        for attempt in range(5):
            log_in(client, user.email, f"Wrong-Password-{attempt}")
        clock.move_to(fixed_now + timedelta(minutes=14, seconds=59))
        assert log_in(client, user.email, TEST_PASSWORD).status_code == 429


@pytest.mark.django_db
def test_four_failures_then_success_resets_the_count(client, user):
    """Helper check: a successful login clears earlier failures."""
    for attempt in range(4):
        log_in(client, user.email, f"Wrong-Password-{attempt}")
    assert log_in(client, user.email, TEST_PASSWORD).status_code == 302
    client.post(reverse("logout"))
    for attempt in range(4):
        log_in(client, user.email, f"Wrong-Password-{attempt}")
    assert log_in(client, user.email, TEST_PASSWORD).status_code == 302


@pytest.mark.django_db
def test_inactive_employee_cannot_log_in(client, user):
    """T-11: an inactive employee with an account cannot log in."""
    employee = user.employee
    employee.status = Employee.Status.INACTIVE
    employee.save()  # D-13 sets User.is_active = False
    response = log_in(client, user.email, TEST_PASSWORD)
    assert response.status_code == 200
    assert "Wrong email or password." in response.content.decode()
    assert logged_in_user_id(client) is None

    # Even if User.is_active were out of step, the directory status still decides.
    User.objects.filter(pk=user.pk).update(is_active=True)
    log_in(client, user.email, TEST_PASSWORD)
    assert logged_in_user_id(client) is None


@pytest.mark.django_db
def test_deactivated_employee_session_ends(client, user):
    """Helper check: someone deactivated while logged in is logged out on the next request."""
    client.force_login(user)
    assert client.get("/").status_code == 200
    Employee.objects.filter(pk=user.employee.pk).update(status=Employee.Status.INACTIVE)
    response = client.get("/")
    assert response.status_code == 302 and response.url.startswith(reverse("login"))


# --- logout and redirects ---------------------------------------------------------------


@pytest.mark.django_db
def test_logout_is_post_only_and_returns_to_login(client, user):
    """Helper check: GET /logout/ is refused; POST logs out and shows a message."""
    client.force_login(user)
    assert client.get(reverse("logout")).status_code == 405
    response = client.post(reverse("logout"))
    assert response.status_code == 302 and response.url == reverse("login")
    assert logged_in_user_id(client) is None
    assert "You have been logged out." in client.get(reverse("login")).content.decode()


@pytest.mark.django_db
def test_logged_in_user_skips_login_and_signup_pages(client, user):
    """Helper check: login and sign-up pages send a logged-in user home."""
    client.force_login(user)
    for name in ("login", "signup"):
        response = client.get(reverse(name))
        assert response.status_code == 302 and response.url == reverse("home")


@pytest.mark.django_db
def test_every_page_requires_login_except_login_and_signup(client):
    """T-58: anonymous users are sent to /login/ from every page except login and sign-up."""
    for path in ("/", "/admin/", "/admin/directory/employee/", reverse("logout")):
        response = client.get(path, follow=True)  # /admin/… goes via /admin/login/
        assert response.redirect_chain[-1] == (f"{reverse('login')}?next={path}", 302), path
        assert response.status_code == 200 and "Log in" in response.content.decode()
    for name in ("login", "signup"):
        assert client.get(reverse(name)).status_code == 200


@pytest.mark.django_db(databases=["default", "payroll"])
def test_axes_and_main_tables_stay_out_of_payroll_database():
    """T-59: django-axes and all non-payroll tables exist only in the main database."""
    main_tables = set(connections["default"].introspection.table_names())
    payroll_tables = set(connections["payroll"].introspection.table_names())
    assert {"axes_accessattempt", "axes_accesslog", "axes_accessfailurelog"} <= main_tables
    assert payroll_tables == {  # Phase 8, plus the adjustments of Change 4
        "django_migrations",
        "payroll_payrollweek",
        "payroll_payrolladjustment",
    }
    assert not {"payroll_payrollweek", "payroll_payrolladjustment"} & main_tables
