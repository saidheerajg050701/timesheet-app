"""Payroll records, stored ONLY in the payroll database (payroll/routers.py, B.6).

Append-only (D-15, D-67): snapshot and hours fields never change after creation; status only
moves CURRENT → EXPORTED → PAID, or any status → SUPERSEDED. Enforced here, in code: save()
checks every change, and delete() / QuerySet.update() / QuerySet.delete() always refuse.
"""

from django.db import models
from django.db.models import Q


class AppendOnlyError(Exception):
    """A change that would break the append-only rules (D-15)."""


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AppendOnlyError("Payroll records can't be bulk-updated; use the payroll services.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise AppendOnlyError("Payroll records can't be bulk-updated; use the payroll services.")

    def delete(self):
        raise AppendOnlyError("Payroll records are never deleted; supersede them instead.")


class PayrollWeek(models.Model):
    class Status(models.TextChoices):
        CURRENT = "CURRENT"
        EXPORTED = "EXPORTED"
        PAID = "PAID"
        SUPERSEDED = "SUPERSEDED"

    # Snapshot fields — plain values, NOT foreign keys (Django can't link across databases)
    employee_code = models.CharField(max_length=20, db_index=True)
    employee_name = models.CharField(max_length=130)
    department = models.CharField(max_length=100)
    team = models.CharField(max_length=100, blank=True)
    week_start = models.DateField(db_index=True)
    period_start = models.DateField(db_index=True)
    regular_minutes = models.PositiveIntegerField()
    overtime_minutes = models.PositiveIntegerField()
    pto_minutes = models.PositiveIntegerField()
    sick_minutes = models.PositiveIntegerField()
    holiday_minutes = models.PositiveIntegerField()
    total_minutes = models.PositiveIntegerField()
    expected_weekly_minutes = models.PositiveIntegerField()  # that week, prorated (D-71)
    approved_by_code = models.CharField(max_length=20)
    approved_by_name = models.CharField(max_length=130)
    approved_at = models.DateTimeField()  # = PeriodApproval.decided_at (D-66)
    source_timesheet_id = models.PositiveIntegerField()  # id in the main database
    version = models.PositiveIntegerField(default=1)
    # Everything above is frozen after creation. Only the fields below may change, forward only.
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CURRENT)
    export_batch = models.CharField(max_length=40, blank=True)
    exported_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee_code", "week_start", "version"], name="one_version_per_week"
            ),
            models.UniqueConstraint(  # at most one live record per employee and week (D-66)
                fields=["employee_code", "week_start"],
                condition=~Q(status="SUPERSEDED"),
                name="one_live_record_per_week",
            ),
        ]

    FROZEN = (
        "employee_code",
        "employee_name",
        "department",
        "team",
        "week_start",
        "period_start",
        "regular_minutes",
        "overtime_minutes",
        "pto_minutes",
        "sick_minutes",
        "holiday_minutes",
        "total_minutes",
        "expected_weekly_minutes",
        "approved_by_code",
        "approved_by_name",
        "approved_at",
        "source_timesheet_id",
        "version",
        "created_at",
    )
    # status → (statuses it may move to, the lifecycle field each move sets)
    MOVES = {
        Status.CURRENT: {Status.EXPORTED: "exported_at", Status.SUPERSEDED: "superseded_at"},
        Status.EXPORTED: {Status.PAID: "paid_at", Status.SUPERSEDED: "superseded_at"},
        Status.PAID: {Status.SUPERSEDED: "superseded_at"},
        Status.SUPERSEDED: {},
    }
    LIFECYCLE = ("export_batch", "exported_at", "paid_at", "superseded_at")

    def __str__(self):
        return f"{self.employee_code} week of {self.week_start} v{self.version} ({self.status})"

    def save(self, *args, **kwargs):
        if self._state.adding:
            if self.status != self.Status.CURRENT or any(getattr(self, f) for f in self.LIFECYCLE):
                raise AppendOnlyError("A new payroll record starts as CURRENT, not exported.")
        else:
            self._check_change()
        super().save(*args, **kwargs)

    def _check_change(self):
        old = type(self).objects.using(self._state.db).get(pk=self.pk)
        for name in self.FROZEN:
            if getattr(old, name) != getattr(self, name):
                raise AppendOnlyError(f"{name} is frozen after creation (D-15).")
        allowed = dict(self.MOVES[old.status])
        changed = {f for f in self.LIFECYCLE if getattr(old, f) != getattr(self, f)}
        if self.status == old.status:
            if changed:
                raise AppendOnlyError(f"{', '.join(sorted(changed))} can't change on its own.")
            return
        if self.status not in allowed:
            raise AppendOnlyError(f"A {old.status} record can't become {self.status} (D-15).")
        expected = {allowed[self.status]} | (
            {"export_batch"} if self.status == self.Status.EXPORTED else set()
        )
        if changed != expected or not all(getattr(self, f) for f in expected):
            fields = ", ".join(sorted(expected))
            raise AppendOnlyError(f"Becoming {self.status} sets exactly {fields}.")

    def delete(self, *args, **kwargs):
        raise AppendOnlyError("Payroll records are never deleted; supersede them instead.")
