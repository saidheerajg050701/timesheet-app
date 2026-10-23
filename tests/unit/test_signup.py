import pytest

from directory.models import Employee
from directory.services.signup import (
    NOT_IN_DIRECTORY,
    Refusal,
    check_signup_eligibility,
    company_domain,
)
from tests.factories import EmployeeFactory, UserFactory


@pytest.mark.django_db
def test_wrong_domain_is_refused():
    """T-01: an email with the wrong domain is refused."""
    EmployeeFactory(email="dev1@yourcompany.com")
    result = check_signup_eligibility("dev1@gmail.com")
    assert not result.ok and result.refusal == Refusal.WRONG_DOMAIN
    assert "@yourcompany.com" in result.message
    # A look-alike domain is also refused.
    assert check_signup_eligibility("dev1@yourcompany.com.evil.io").refusal == Refusal.WRONG_DOMAIN


@pytest.mark.django_db
def test_email_not_in_directory_is_refused_with_contact_hr():
    """T-02: an email not in the directory is refused with "Contact HR"."""
    result = check_signup_eligibility("nobody@yourcompany.com")
    assert result.refusal == Refusal.NOT_IN_DIRECTORY
    assert result.message == NOT_IN_DIRECTORY
    assert "not in the company employee directory" in result.message
    assert "Contact HR" in result.message


@pytest.mark.django_db
def test_inactive_employee_is_refused():
    """T-03: an INACTIVE employee is refused (same message as not in directory)."""
    EmployeeFactory(email="former@yourcompany.com", status=Employee.Status.INACTIVE)
    result = check_signup_eligibility("former@yourcompany.com")
    assert result.refusal == Refusal.INACTIVE
    assert result.message == NOT_IN_DIRECTORY


@pytest.mark.django_db
def test_existing_account_is_refused():
    """T-04: an employee who already has an account gets "already exists"."""
    user = UserFactory()
    result = check_signup_eligibility(user.email.upper())
    assert result.refusal == Refusal.ACCOUNT_EXISTS
    assert result.message == "An account already exists — please log in."


@pytest.mark.django_db
def test_eligible_email_is_normalised(employee):
    """Helper check: trimmed and lower-cased before checking; eligible employee returned."""
    result = check_signup_eligibility(f"  {employee.email.upper()}  ")
    assert result.ok and result.message == ""
    assert result.email == employee.email and result.employee == employee


def test_company_domain_always_starts_with_at(settings):
    """Helper check: COMPANY_EMAIL_DOMAIN works with or without the leading @."""
    settings.COMPANY_EMAIL_DOMAIN = "YourCompany.com"
    assert company_domain() == "@yourcompany.com"
    settings.COMPANY_EMAIL_DOMAIN = "@yourcompany.com"
    assert company_domain() == "@yourcompany.com"
