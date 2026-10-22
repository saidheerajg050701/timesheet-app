from django.contrib.auth.base_user import BaseUserManager

from directory.services.accounts import account_fields_for, check_superuser_candidate


class UserManager(BaseUserManager):
    """Email login; every account belongs to an employee (D-02).

    Email and the is_staff / is_superuser / is_active flags always come from the
    employee record (D-13, D-20), never from the caller.
    """

    use_in_migrations = True

    def create_user(self, email=None, password=None, *, employee=None, **extra_fields):
        if employee is None:
            raise ValueError("An account must be linked to an employee.")
        if email is not None and email.strip().lower() != employee.email.strip().lower():
            raise ValueError("The account email must match the employee's directory email.")
        # Directory values win over anything passed in extra_fields.
        user = self.model(employee=employee, **{**extra_fields, **account_fields_for(employee)})
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, password=None, *, employee=None, **extra_fields):
        if employee is None:
            raise ValueError("An account must be linked to an employee.")
        check_superuser_candidate(employee)
        return self.create_user(email, password, employee=employee, **extra_fields)
