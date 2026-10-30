# Refactor R2 (D-174): PayRecord moves from the directory app to the compensation app.
# State only: Django's record of the model changes; the table directory_payrecord and every
# row stay exactly where they are.

import decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("directory", "0003_payrecord"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="PayRecord",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("pay_type", models.CharField(choices=[("SALARIED", "Salaried"), ("HOURLY", "Hourly")], max_length=10)),
                        ("annual_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                        ("hourly_rate", models.DecimalField(decimal_places=2, max_digits=9, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])),
                        ("effective_from", models.DateField()),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("system_actor", models.CharField(blank=True, max_length=40)),
                        ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="directory.employee")),
                        ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pay_records", to="directory.employee")),
                    ],
                    options={
                        "db_table": "directory_payrecord",
                        "ordering": ("employee_id", "effective_from", "pk"),
                        "constraints": [
                            models.CheckConstraint(condition=models.Q(("hourly_rate__gt", 0)), name="pay_rate_positive"),
                            models.CheckConstraint(condition=models.Q(models.Q(("annual_salary__gt", 0), ("pay_type", "SALARIED")), models.Q(("annual_salary__isnull", True), ("pay_type", "HOURLY")), _connector="OR"), name="pay_salary_only_when_salaried"),
                        ],
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
