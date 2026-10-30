from django.contrib.auth.backends import ModelBackend

from apps.directory.models import Employee


class EmployeeBackend(ModelBackend):
    """Email + password login for ACTIVE employees only (FR-1).

    User.is_active already follows Employee.status (D-13); checking the directory too means
    an inactive employee can never log in, and an existing session ends on the next request.
    """

    def user_can_authenticate(self, user):
        employee = getattr(user, "employee", None)
        return (
            super().user_can_authenticate(user)
            and employee is not None
            and employee.status == Employee.Status.ACTIVE
        )
