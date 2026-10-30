"""Sign-up with the employee directory check (FR-2)."""

from dataclasses import dataclass
from enum import StrEnum

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.audit.models import AuditLog
from apps.audit.services.log import record
from apps.directory.models import Employee

NOT_IN_DIRECTORY = "This email is not in the company employee directory. Contact HR."
ACCOUNT_EXISTS = "An account already exists — please log in."


class Refusal(StrEnum):
    WRONG_DOMAIN = "WRONG_DOMAIN"
    NOT_IN_DIRECTORY = "NOT_IN_DIRECTORY"
    INACTIVE = "INACTIVE"
    ACCOUNT_EXISTS = "ACCOUNT_EXISTS"


def company_domain():
    domain = settings.COMPANY_EMAIL_DOMAIN.strip().lower()
    return domain if domain.startswith("@") else f"@{domain}"


def normalize_email(raw):
    return (raw or "").strip().lower()


@dataclass(frozen=True)
class Eligibility:
    email: str
    employee: Employee | None = None
    refusal: Refusal | None = None

    @property
    def ok(self):
        return self.refusal is None

    @property
    def message(self):
        if self.refusal == Refusal.WRONG_DOMAIN:
            return f"Use your company email address (ending in {company_domain()})."
        if self.refusal in (Refusal.NOT_IN_DIRECTORY, Refusal.INACTIVE):
            # Same text for both, so the page never reveals someone's employment status.
            return NOT_IN_DIRECTORY
        if self.refusal == Refusal.ACCOUNT_EXISTS:
            return ACCOUNT_EXISTS
        return ""


def check_signup_eligibility(email):
    """FR-2 steps 1–3: company domain, ACTIVE directory entry, no account yet."""
    email = normalize_email(email)
    if not email.endswith(company_domain()):
        return Eligibility(email, refusal=Refusal.WRONG_DOMAIN)
    employee = Employee.objects.filter(email=email).first()
    if employee is None:
        return Eligibility(email, refusal=Refusal.NOT_IN_DIRECTORY)
    if employee.status != Employee.Status.ACTIVE:
        return Eligibility(email, employee, Refusal.INACTIVE)
    if get_user_model().objects.filter(employee=employee).exists():
        return Eligibility(email, employee, Refusal.ACCOUNT_EXISTS)
    return Eligibility(email, employee)


def create_account(eligibility, password):
    """FR-2 step 4: create the account (Argon2 hash) linked to the directory record.

    Returns (user, None), or (None, Eligibility) if someone else created it meanwhile.
    """
    try:
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                password=password, employee=eligibility.employee
            )
            record(
                AuditLog.Action.CREATE,
                "User",
                user.email,
                actor=eligibility.employee,
                after={"email": user.email, "via": "sign-up"},
            )
    except IntegrityError:
        return None, Eligibility(eligibility.email, eligibility.employee, Refusal.ACCOUNT_EXISTS)
    return user, None
