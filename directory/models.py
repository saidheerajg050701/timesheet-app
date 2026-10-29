from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models, transaction

from directory.managers import UserManager
from directory.services.accounts import sync_account


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


class PayHistoryError(Exception):
    """Pay records are history: a saved record is never changed or deleted (D-166)."""


class PayRecordQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PayHistoryError("Pay records are never changed; add a pay change instead.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise PayHistoryError("Pay records are never changed; add a pay change instead.")

    def delete(self):
        raise PayHistoryError("Pay records are never deleted.")


class PayRecord(models.Model):
    """One pay setting from a date on (Change 12, D-166). Admin-only; append-only history: a
    pay change, or a correction for the same date, is a new record. The record in force on a
    day is the one with the latest effective_from up to that day (the newest for a tie) —
    directory/services/pay.py."""

    class PayType(models.TextChoices):
        SALARIED = "SALARIED", "Salaried"
        HOURLY = "HOURLY", "Hourly"

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="pay_records")
    pay_type = models.CharField(max_length=10, choices=PayType.choices)
    annual_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    hourly_rate = models.DecimalField(  # USD, exact cents
        max_digits=9, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    effective_from = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        Employee, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    system_actor = models.CharField(max_length=40, blank=True)  # e.g. "seed_demo"

    objects = PayRecordQuerySet.as_manager()

    class Meta:
        ordering = ("employee_id", "effective_from", "pk")
        constraints = [
            models.CheckConstraint(condition=models.Q(hourly_rate__gt=0), name="pay_rate_positive"),
            models.CheckConstraint(
                condition=models.Q(pay_type="SALARIED", annual_salary__gt=0)
                | models.Q(pay_type="HOURLY", annual_salary__isnull=True),
                name="pay_salary_only_when_salaried",
            ),
        ]

    def __str__(self):  # no amounts: pay never shows up in logs or error pages (D-167)
        return f"Pay of {self.employee.employee_code} from {self.effective_from}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PayHistoryError("Pay records are never changed; add a pay change instead.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PayHistoryError("Pay records are never deleted.")
