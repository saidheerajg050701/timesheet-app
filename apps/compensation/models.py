"""Employee pay (D-166, D-167). Moved from the directory app in Refactor R2 (D-174): the
table keeps its name (directory_payrecord), so no row moved."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


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
    apps/compensation/services/pay.py."""

    class PayType(models.TextChoices):
        SALARIED = "SALARIED", "Salaried"
        HOURLY = "HOURLY", "Hourly"

    employee = models.ForeignKey(
        "directory.Employee", on_delete=models.PROTECT, related_name="pay_records"
    )
    pay_type = models.CharField(max_length=10, choices=PayType.choices)
    annual_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    hourly_rate = models.DecimalField(  # USD, exact cents
        max_digits=9, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    effective_from = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "directory.Employee", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    system_actor = models.CharField(max_length=40, blank=True)  # e.g. "seed_demo"

    objects = PayRecordQuerySet.as_manager()

    class Meta:
        db_table = "directory_payrecord"  # the table it always had (D-174)
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
