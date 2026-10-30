from django.contrib.auth.models import AbstractUser
from django.db import models, transaction

from apps.directory.managers import UserManager
from apps.directory.services.accounts import sync_account


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    department = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Employee(models.Model):  # the company employee directory
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        INACTIVE = "INACTIVE"

    employee_code = models.CharField(max_length=20, unique=True)  # Employee ID, e.g. EMP-0004
    email = models.EmailField(unique=True)  # stored lower-case; source of truth (D-20)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    job_title = models.CharField(max_length=100)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    manager = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reports"
    )
    location = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)  # set on deactivation (D-19)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    expected_weekly_minutes = models.PositiveIntegerField(default=2400)  # 40 h
    is_admin = models.BooleanField(default=False)
    is_payroll = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.employee_code} {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        # The linked User follows the directory on every save (D-13, D-20). Both writes
        # share one transaction, so an email clash rolls back the Employee change too.
        with transaction.atomic():
            super().save(*args, **kwargs)
            sync_account(self)


class User(AbstractUser):  # login account — exists before the first migrate (D-02)
    username = None
    email = models.EmailField(unique=True)  # always mirrors employee.email (D-20)
    employee = models.OneToOneField(Employee, on_delete=models.PROTECT, related_name="account")
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    # Set by an HR password reset; every page sends the person to Profile until they pick a
    # new password (D-91).
    must_change_password = models.BooleanField(default=False)
    objects = UserManager()
    # The inherited "password" field stores only the Argon2 hash, e.g. "argon2$argon2id$v=19$..."

    def __str__(self):
        return self.email
