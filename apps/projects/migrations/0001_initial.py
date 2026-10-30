# Refactor R2 (D-174): Project and Task move from the timesheets app to the projects app.
# State only: Django's record of the models changes; the tables (timesheets_project,
# timesheets_task, timesheets_project_tasks) and every row stay exactly where they are.

import decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("timesheets", "0009_project_budget"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Task",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("code", models.CharField(max_length=10, unique=True)),
                        ("name", models.CharField(max_length=80)),
                        ("description", models.TextField(blank=True)),
                        ("active", models.BooleanField(default=True)),
                        ("sort_order", models.PositiveSmallIntegerField(default=0)),
                    ],
                    options={
                        "db_table": "timesheets_task",
                        "ordering": ("sort_order", "code"),
                    },
                ),
                migrations.CreateModel(
                    name="Project",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("number", models.PositiveIntegerField(unique=True)),
                        ("code", models.CharField(max_length=20, unique=True)),
                        ("name", models.CharField(max_length=120)),
                        ("active", models.BooleanField(default=True)),
                        ("budget", models.DecimalField(blank=True, decimal_places=2, help_text='USD. Leave empty for "No budget set".', max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))])),
                        ("costs_from", models.DateField(blank=True, help_text="Costs count from this date (empty: all time).", null=True)),
                        ("tasks", models.ManyToManyField(blank=True, related_name="projects", to="projects.task")),
                    ],
                    options={
                        "db_table": "timesheets_project",
                        "ordering": ("number",),
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
