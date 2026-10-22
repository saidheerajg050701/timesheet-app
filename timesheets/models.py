from django.db import models


class Project(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} {self.name}"


class Timesheet(models.Model):  # one per employee per week
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        SUBMITTED = "SUBMITTED"
        LOCKED = "LOCKED"
        REOPENED = "REOPENED"
        APPROVED = "APPROVED"

    employee = models.ForeignKey(
        "directory.Employee", on_delete=models.PROTECT, related_name="timesheets"
    )
    week_start = models.DateField()  # always a Monday
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    # to/from APPROVED only via timesheets/services/approvals.py (D-10)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_late = models.BooleanField(default=False)
    reopen_until = models.DateTimeField(null=True, blank=True)
    manager_note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["employee", "week_start"], name="one_sheet_per_week")
        ]

    def __str__(self):
        return f"{self.employee.employee_code} week of {self.week_start}"


class TimeEntry(models.Model):
    class Category(models.TextChoices):
        PROJECT = "PROJECT"
        MEETING = "MEETING"
        TRAINING = "TRAINING"
        PTO = "PTO"
        SICK = "SICK"
        HOLIDAY = "HOLIDAY"
        OTHER = "OTHER"

    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE, related_name="entries")
    work_date = models.DateField()  # within the week and within hire_date…end_date (D-19)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.PROTECT)
    # PROJECT entries must have an active project; all other categories must have none (D-18)
    category = models.CharField(max_length=10, choices=Category.choices)
    minutes = models.PositiveIntegerField()  # multiple of 15; daily total ≤ 1440
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.work_date} {self.category} {self.minutes} min"


class PeriodApproval(models.Model):  # one per employee per 2-week period
    class Status(models.TextChoices):
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"

    employee = models.ForeignKey("directory.Employee", on_delete=models.PROTECT)
    period_start = models.DateField()  # Monday of week 1
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    approver = models.ForeignKey(
        "directory.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approvals_made",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.employee.employee_code} period of {self.period_start}: {self.status}"


class ChangeRequest(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN"
        REJECTED = "REJECTED"
        UNLOCKED = "UNLOCKED"
        EDITED = "EDITED"

    timesheet = models.ForeignKey(
        Timesheet, on_delete=models.CASCADE, related_name="change_requests"
    )
    requester = models.ForeignKey("directory.Employee", on_delete=models.PROTECT)
    # requester is the manager for an Unlock from the approval page (D-06)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    reviewer = models.ForeignKey(
        "directory.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requests_reviewed",
    )
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Change request #{self.pk} ({self.status})"
