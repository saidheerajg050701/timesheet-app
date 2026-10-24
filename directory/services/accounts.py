"""Login accounts and their link to the employee directory (D-02, D-13, D-20)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


def account_fields_for(employee):
    """The User fields that always mirror the employee record."""
    return {
        "email": employee.email.strip().lower(),
        "is_staff": employee.is_admin,
        "is_superuser": employee.is_admin,
        "is_active": employee.status == employee.Status.ACTIVE,
    }


def sync_account(employee):
    """Copy is_admin, status and email from the employee to its linked User, if any.

    Called from Employee.save(). Returns the number of accounts updated (0 or 1).
    """
    return get_user_model().objects.filter(employee=employee).update(**account_fields_for(employee))


def check_superuser_candidate(employee):
    """Raise ValidationError unless the employee may get a superuser account (D-02, D-23)."""
    if employee.status != employee.Status.ACTIVE:
        raise ValidationError(f"Employee {employee.employee_code} is not ACTIVE.")
    if not employee.is_admin:
        raise ValidationError(
            f"Employee {employee.employee_code} is not a directory admin (is_admin is off). "
            "Set is_admin on the employee first."
        )
    if get_user_model().objects.filter(employee=employee).exists():
        raise ValidationError(f"Employee {employee.employee_code} already has an account.")


def superuser_candidate(employee_code):
    """Look up an employee by code and check it may get a superuser account."""
    from directory.models import Employee

    code = employee_code.strip().upper()
    try:
        employee = Employee.objects.get(employee_code=code)
    except Employee.DoesNotExist:
        raise ValidationError(f"No employee with code {code}.") from None
    check_superuser_candidate(employee)
    return employee


def change_password(user, new_password):
    """Store a new Argon2 hash and audit the change. The audit row holds no password data.

    Used by the profile page; clears a pending forced change after an HR reset (D-91).
    """
    from audit.models import AuditLog  # imported here: this module loads with directory.models
    from audit.services.log import record

    user.set_password(new_password)
    user.must_change_password = False  # an HR reset is done once they pick their own (D-91)
    user.save(update_fields=["password", "must_change_password"])
    record(
        AuditLog.Action.UPDATE,
        "User",
        user.email,
        actor=user.employee,
        after={"changed": ["password"]},
    )
