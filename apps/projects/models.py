"""Projects and their tasks (D-148–D-155, D-168). Moved from timesheets in Refactor R2
(D-174): the tables keep their names (timesheets_project, timesheets_task,
timesheets_project_tasks), so no row moved."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Task(models.Model):
    """What project work was spent on, e.g. DEV Development (Change 10, D-148). Admin-managed,
    never deleted (deactivate instead); the code is fixed once added."""

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "timesheets_task"  # the table it always had (D-174)
        ordering = ("sort_order", "code")

    def __str__(self):
        return f"{self.code} {self.name}"


class Project(models.Model):
    """A project, coded I-001, I-002, … — assigned by the app, never typed or edited
    (apps/projects/services/projects.py, D-155)."""

    number = models.PositiveIntegerField(unique=True)  # the I-code's number; sorts I-999 < I-1000
    code = models.CharField(max_length=20, unique=True)  # "I-" + number, at least 3 digits
    name = models.CharField(max_length=120)
    active = models.BooleanField(default=True)
    # The tasks project work on this project may be booked to (D-149)
    tasks = models.ManyToManyField(Task, blank=True, related_name="projects")
    # Change 12 (D-168): optional budget in USD, compared with the labour cost of approved
    # project hours since costs_from (all time when empty)
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text='USD. Leave empty for "No budget set".',
    )
    costs_from = models.DateField(
        null=True,
        blank=True,
        help_text="Costs count from this date (empty: all time).",
    )

    class Meta:
        db_table = "timesheets_project"  # the table it always had (D-174)
        ordering = ("number",)

    def __str__(self):
        return f"{self.code} {self.name}"
