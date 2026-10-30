from io import StringIO

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError

from directory.models import Employee, User
from tests.factories import EmployeeFactory, UserFactory

PASSWORD = "Long-Enough-Pass-1"


@pytest.fixture
def superuser_password(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", PASSWORD)


def run_createsuperuser(*args):
    out = StringIO()
    call_command("createsuperuser", *args, stdout=out, stderr=StringIO())
    return out.getvalue()


# --- D-02: accounts always belong to an employee ---------------------------------------


@pytest.mark.django_db
def test_account_requires_an_employee():
    """T-44: create_user / create_superuser without an employee are refused (D-02)."""
    with pytest.raises(ValueError, match="linked to an employee"):
        User.objects.create_user("someone@yourcompany.com", PASSWORD)
    with pytest.raises(ValueError, match="linked to an employee"):
        User.objects.create_superuser("someone@yourcompany.com", PASSWORD)
    assert not User.objects.exists()


@pytest.mark.django_db
def test_create_user_takes_email_and_flags_from_employee():
    """T-45: create_user takes the lower-cased email and all flags from the employee."""
    admin = EmployeeFactory(email="  Mixed.Case@YourCompany.com ", is_admin=True)
    user = User.objects.create_user(password=PASSWORD, employee=admin, is_staff=False)
    assert user.email == "mixed.case@yourcompany.com"
    assert (user.is_staff, user.is_superuser, user.is_active) == (True, True, True)

    former = EmployeeFactory(status=Employee.Status.INACTIVE)
    user = User.objects.create_user(password=PASSWORD, employee=former)
    assert (user.is_staff, user.is_superuser, user.is_active) == (False, False, False)


@pytest.mark.django_db
def test_create_user_refuses_an_email_that_differs_from_the_directory(employee):
    """Helper check: an explicit email must match the employee's directory email."""
    with pytest.raises(ValueError, match="must match"):
        User.objects.create_user("other@yourcompany.com", PASSWORD, employee=employee)
    user = User.objects.create_user(employee.email.upper(), PASSWORD, employee=employee)
    assert user.email == employee.email


@pytest.mark.django_db
def test_create_superuser_refuses_non_admin_employee(employee):
    """Helper check: the manager itself refuses a non-admin employee (D-23)."""
    with pytest.raises(ValidationError, match="not a directory admin"):
        User.objects.create_superuser(password=PASSWORD, employee=employee)
    assert not User.objects.exists()


# --- D-02 / D-23: createsuperuser starts from an employee_code ---------------------------


@pytest.mark.django_db
def test_createsuperuser_refuses_ineligible_employees(superuser_password):
    """T-46: createsuperuser refuses unknown, INACTIVE, non-admin or already-linked codes."""
    EmployeeFactory(employee_code="EMP-0101", is_admin=True, status=Employee.Status.INACTIVE)
    EmployeeFactory(employee_code="EMP-0102", is_admin=False)
    UserFactory(employee__employee_code="EMP-0103", employee__is_admin=True)
    refusals = {
        "EMP-9999": "No employee with code EMP-9999",
        "EMP-0101": "not ACTIVE",
        "EMP-0102": "not a directory admin",
        "EMP-0103": "already has an account",
    }
    for code, message in refusals.items():
        with pytest.raises(CommandError, match=message):
            run_createsuperuser("--noinput", "--employee-code", code)
    assert User.objects.count() == 1  # only the pre-existing EMP-0103 account


@pytest.mark.django_db
def test_createsuperuser_creates_admin_account_for_active_admin_employee(superuser_password):
    """T-47: createsuperuser links a superuser to an ACTIVE admin employee without an account."""
    hr = EmployeeFactory(employee_code="EMP-0007", email="hr@yourcompany.com", is_admin=True)
    output = run_createsuperuser("--noinput", "--employee-code", " emp-0007 ")
    user = User.objects.get()
    assert user.employee == hr
    assert user.email == "hr@yourcompany.com"
    assert user.is_staff and user.is_superuser and user.is_active
    assert user.password.startswith("argon2")
    assert user.check_password(PASSWORD)
    assert PASSWORD not in output


@pytest.mark.django_db
def test_createsuperuser_noinput_needs_code_and_strong_password(monkeypatch, admin_employee):
    """Helper check: --noinput needs --employee-code and a valid DJANGO_SUPERUSER_PASSWORD."""
    code = admin_employee.employee_code
    with pytest.raises(CommandError, match="--employee-code is required"):
        run_createsuperuser("--noinput")
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)
    with pytest.raises(CommandError, match="DJANGO_SUPERUSER_PASSWORD"):
        run_createsuperuser("--noinput", "--employee-code", code)
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "short")
    with pytest.raises(CommandError, match="too short"):
        run_createsuperuser("--noinput", "--employee-code", code)
    assert not User.objects.exists()


@pytest.mark.django_db
def test_createsuperuser_interactive_reprompts_until_valid(monkeypatch, employee, admin_employee):
    """Helper check: interactive mode re-asks after a refused code, mismatch or weak password."""
    codes = iter([employee.employee_code, admin_employee.employee_code])
    passwords = iter(["one-Password-1", "two-Password-2", "short", "short", PASSWORD, PASSWORD])
    monkeypatch.setattr("builtins.input", lambda prompt: next(codes))
    monkeypatch.setattr("getpass.getpass", lambda prompt: next(passwords))
    err = StringIO()
    call_command("createsuperuser", stdout=StringIO(), stderr=err)
    user = User.objects.get()
    assert user.employee == admin_employee and user.is_superuser
    assert "not a directory admin" in err.getvalue()
    assert "didn't match" in err.getvalue()
    assert "too short" in err.getvalue()
    assert PASSWORD not in err.getvalue()


# --- D-13: flags follow the directory on every Employee save -----------------------------


@pytest.mark.django_db
def test_admin_flag_controls_staff_and_superuser(user):
    """T-48: switching Employee.is_admin on and off updates is_staff and is_superuser (D-13)."""
    employee = user.employee
    employee.is_admin = True
    employee.save()
    user.refresh_from_db()
    assert user.is_staff and user.is_superuser

    employee.is_admin = False
    employee.save()
    user.refresh_from_db()
    assert not user.is_staff and not user.is_superuser


@pytest.mark.django_db
def test_employee_status_controls_is_active(user):
    """T-49: setting the employee INACTIVE then ACTIVE updates User.is_active (D-13)."""
    employee = user.employee
    employee.status = Employee.Status.INACTIVE
    employee.save()
    user.refresh_from_db()
    assert not user.is_active

    employee.status = Employee.Status.ACTIVE
    employee.save()
    user.refresh_from_db()
    assert user.is_active


# --- D-20: Employee.email is the source of truth ------------------------------------------


@pytest.mark.django_db
def test_email_change_in_directory_updates_account(user):
    """T-50: HR changing Employee.email updates both emails, lower-cased (D-20)."""
    employee = user.employee
    employee.email = "  New.Address@YourCompany.COM "
    employee.save()
    employee.refresh_from_db()
    user.refresh_from_db()
    assert employee.email == user.email == "new.address@yourcompany.com"
    assert user.check_password("Test-Password-123!")


@pytest.mark.django_db
def test_emails_stay_unique_regardless_of_case():
    """T-51: an employee cannot take an existing email in different case (D-20)."""
    taken = UserFactory(employee__email="taken@yourcompany.com")
    other = UserFactory()
    original = other.email

    other.employee.email = "TAKEN@YourCompany.com"
    with pytest.raises(IntegrityError):
        other.employee.save()
    with pytest.raises(IntegrityError):
        EmployeeFactory(email="Taken@yourcompany.com")

    other.employee.refresh_from_db()
    other.refresh_from_db()
    taken.refresh_from_db()
    assert other.employee.email == other.email == original
    assert taken.email == "taken@yourcompany.com"
