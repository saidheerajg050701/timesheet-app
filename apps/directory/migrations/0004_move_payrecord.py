# Refactor R2 (D-174): PayRecord now belongs to the compensation app. State only: the table
# directory_payrecord and its rows are untouched.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("directory", "0003_payrecord"),
        ("compensation", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.DeleteModel(name="PayRecord")],
            database_operations=[],
        ),
    ]
