"""Payroll records, stored ONLY in the payroll database (payroll/routers.py, B.6).

Append-only (D-15, D-67, D-120): snapshot and hours fields never change after creation; the
status only moves forward along MOVES. Enforced here, in code: save() checks every change, and
delete() / QuerySet.update() / QuerySet.delete() always refuse.

Week records move CURRENT → EXPORTED → PAID, or CURRENT → SETTLED for a corrected version of a
week that was already exported (paid through adjustments instead, D-118), and any of them →
SUPERSEDED. Adjustments (the difference a correction makes) move CURRENT → EXPORTED → PAID.
A pay period's register is saved when it is finalized and moves FINALIZED → PAID; its lines
never change at all (D-132).
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


class AppendOnlyRecord(models.Model):
    """Shared append-only rules: FROZEN fields never change; the status follows MOVES, and
    each move sets exactly its own LIFECYCLE field (plus export_batch when exporting)."""

    FROZEN = ()
    MOVES = {}
    LIFECYCLE = ()
    INITIAL_STATUS = "CURRENT"  # the status every new record starts with
    EXPORT_STATUS = "EXPORTED"  # the move that also sets export_batch

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self._state.adding:
            if self.status != self.INITIAL_STATUS or any(getattr(self, f) for f in self.LIFECYCLE):
                raise AppendOnlyError(
                    f"A new payroll record starts as {self.INITIAL_STATUS}, not further on."
                )
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
            {"export_batch"} if self.status == self.EXPORT_STATUS else set()
        )
        if changed != expected or not all(getattr(self, f) for f in expected):
            fields = ", ".join(sorted(expected))
            raise AppendOnlyError(f"Becoming {self.status} sets exactly {fields}.")

    def delete(self, *args, **kwargs):
        raise AppendOnlyError("Payroll records are never deleted; supersede them instead.")


class PayrollWeek(AppendOnlyRecord):
    class Status(models.TextChoices):
        CURRENT = "CURRENT"
        EXPORTED = "EXPORTED"
        PAID = "PAID"
        SETTLED = "SETTLED"  # paid through adjustments, never exported as a week (D-118)
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
    settled_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
        Status.CURRENT: {
            Status.EXPORTED: "exported_at",
            Status.SETTLED: "settled_at",
            Status.SUPERSEDED: "superseded_at",
        },
        Status.EXPORTED: {Status.PAID: "paid_at", Status.SUPERSEDED: "superseded_at"},
        Status.PAID: {Status.SUPERSEDED: "superseded_at"},
        Status.SETTLED: {Status.SUPERSEDED: "superseded_at"},
        Status.SUPERSEDED: {},
    }
    LIFECYCLE = ("export_batch", "exported_at", "paid_at", "settled_at", "superseded_at")

    def __str__(self):
        return f"{self.employee_code} week of {self.week_start} v{self.version} ({self.status})"


class PayrollAdjustment(AppendOnlyRecord):
    """The difference a correction makes to a week that was already exported or paid,
    carried forward to the next pay run (D-119–D-121). Amounts are signed minutes."""

    class Status(models.TextChoices):
        CURRENT = "CURRENT"
        EXPORTED = "EXPORTED"
        PAID = "PAID"

    # Snapshot fields — plain values, frozen after creation
    employee_code = models.CharField(max_length=20, db_index=True)
    employee_name = models.CharField(max_length=130)
    department = models.CharField(max_length=100)
    team = models.CharField(max_length=100, blank=True)
    week_start = models.DateField()  # the corrected week
    week_period_start = models.DateField()  # that week's own pay period
    period_start = models.DateField(db_index=True)  # the pay period it is carried to (D-121)
    old_version = models.PositiveIntegerField()
    new_version = models.PositiveIntegerField()
    regular_minutes = models.IntegerField()
    overtime_minutes = models.IntegerField()
    pto_minutes = models.IntegerField()
    sick_minutes = models.IntegerField()
    holiday_minutes = models.IntegerField()
    total_minutes = models.IntegerField()
    approved_by_code = models.CharField(max_length=20)
    approved_by_name = models.CharField(max_length=130)
    approved_at = models.DateTimeField()
    reason = models.TextField()  # shown on Corrections only, never in the CSV (D-122)
    source_timesheet_id = models.PositiveIntegerField()
    # Lifecycle, forward only
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CURRENT)
    export_batch = models.CharField(max_length=40, blank=True)
    exported_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee_code", "week_start", "new_version"],
                name="one_adjustment_per_version",
            )
        ]

    FROZEN = (
        "employee_code",
        "employee_name",
        "department",
        "team",
        "week_start",
        "week_period_start",
        "period_start",
        "old_version",
        "new_version",
        "regular_minutes",
        "overtime_minutes",
        "pto_minutes",
        "sick_minutes",
        "holiday_minutes",
        "total_minutes",
        "approved_by_code",
        "approved_by_name",
        "approved_at",
        "reason",
        "source_timesheet_id",
        "created_at",
    )
    MOVES = {
        Status.CURRENT: {Status.EXPORTED: "exported_at"},
        Status.EXPORTED: {Status.PAID: "paid_at"},
        Status.PAID: {},
    }
    LIFECYCLE = ("export_batch", "exported_at", "paid_at")
    AMOUNTS = ("regular", "overtime", "pto", "sick", "holiday", "total")

    def __str__(self):
        return (
            f"{self.employee_code} adjustment for {self.week_start} "
            f"v{self.old_version}→v{self.new_version} ({self.status})"
        )


class PayrollRegister(AppendOnlyRecord):
    """A pay period's register, saved by "Finalize & export" (D-132, D-135): one batch for the
    period, frozen lines, then Mark as paid. OPEN and READY are never saved — they are worked
    out live, because an approval can still go back to PENDING (payroll/services/register.py)."""

    class Status(models.TextChoices):
        FINALIZED = "FINALIZED", "Finalized & exported"
        PAID = "PAID", "Paid"

    class Ready(models.TextChoices):
        ALL_APPROVED = "ALL_APPROVED", "Everyone approved"
        DEADLINE = "DEADLINE", "Approval deadline passed"
        BACKFILL = "BACKFILL", "Built from earlier exports"

    period_start = models.DateField(unique=True)
    period_end = models.DateField()
    export_batch = models.CharField(max_length=200)  # "EXP-0007"; older data may join several
    ready_reason = models.CharField(max_length=12, choices=Ready.choices)
    required_count = models.PositiveIntegerField()  # who had to be approved, at finalizing
    approved_count = models.PositiveIntegerField()
    finalized_at = models.DateTimeField()
    finalized_by_code = models.CharField(max_length=20, blank=True)
    finalized_by_name = models.CharField(max_length=130)  # a person, or the system actor
    # Lifecycle, forward only
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.FINALIZED)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    INITIAL_STATUS = Status.FINALIZED
    EXPORT_STATUS = None
    FROZEN = (
        "period_start",
        "period_end",
        "export_batch",
        "ready_reason",
        "required_count",
        "approved_count",
        "finalized_at",
        "finalized_by_code",
        "finalized_by_name",
        "created_at",
    )
    MOVES = {Status.FINALIZED: {Status.PAID: "paid_at"}, Status.PAID: {}}
    LIFECYCLE = ("paid_at",)

    def __str__(self):
        return f"Register {self.period_start} ({self.status}, {self.export_batch})"

    @property
    def batches(self):
        return self.export_batch.split("+")


class FrozenRecord(models.Model):
    """Saved once, never changed or deleted (register lines, D-132)."""

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AppendOnlyError("Register lines never change once the register is finalized.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AppendOnlyError("Register lines are never deleted.")


CATEGORIES = ("regular", "overtime", "pto", "sick", "holiday")


class PayrollRegisterLine(FrozenRecord):
    """One employee's line in a finalized register (D-134). Minutes; Period and Pay totals are
    worked out from the stored columns, so they can never disagree with them."""

    class Status(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        NOT_SUBMITTED = "NOT_SUBMITTED", "Missed – not submitted"
        AWAITING = "AWAITING", "Waiting for manager approval"
        CARRY_ONLY = "CARRY_ONLY", "Carry-forward only"

    register = models.ForeignKey(PayrollRegister, on_delete=models.PROTECT, related_name="lines")
    employee_code = models.CharField(max_length=20, db_index=True)
    employee_name = models.CharField(max_length=130)
    department = models.CharField(max_length=100)
    team = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=14, choices=Status.choices)
    approved_by_code = models.CharField(max_length=20, blank=True)
    approved_by_name = models.CharField(max_length=130, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    week1_regular_minutes = models.PositiveIntegerField(default=0)
    week1_overtime_minutes = models.PositiveIntegerField(default=0)
    week1_pto_minutes = models.PositiveIntegerField(default=0)
    week1_sick_minutes = models.PositiveIntegerField(default=0)
    week1_holiday_minutes = models.PositiveIntegerField(default=0)
    week2_regular_minutes = models.PositiveIntegerField(default=0)
    week2_overtime_minutes = models.PositiveIntegerField(default=0)
    week2_pto_minutes = models.PositiveIntegerField(default=0)
    week2_sick_minutes = models.PositiveIntegerField(default=0)
    week2_holiday_minutes = models.PositiveIntegerField(default=0)
    # Carried forward into this register: adjustments and late-approved weeks (signed, D-136)
    carry_regular_minutes = models.IntegerField(default=0)
    carry_overtime_minutes = models.IntegerField(default=0)
    carry_pto_minutes = models.IntegerField(default=0)
    carry_sick_minutes = models.IntegerField(default=0)
    carry_holiday_minutes = models.IntegerField(default=0)
    carry_total_minutes = models.IntegerField(default=0)
    carry_from = models.JSONField(default=list)  # [{"week", "kind", "total_minutes"}, …]
    week_record_ids = models.JSONField(default=list)  # what this line paid (traceability)
    adjustment_ids = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["register", "employee_code"], name="one_line_per_employee"
            )
        ]

    def __str__(self):
        return f"{self.employee_code} in {self.register.period_start}"

    def period(self, category):
        return getattr(self, f"week1_{category}_minutes") + getattr(
            self, f"week2_{category}_minutes"
        )

    @property
    def period_total_minutes(self):
        return sum(self.period(c) for c in CATEGORIES)

    @property
    def pay_total_minutes(self):
        return self.period_total_minutes + self.carry_total_minutes
