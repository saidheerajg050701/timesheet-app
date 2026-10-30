# Refactor R2 (D-174): Project and Task now belong to the projects app. State only: the time
# entries keep their project_id and task_id columns pointing at the same tables; nothing is
# copied or dropped.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("timesheets", "0009_project_budget"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="timeentry",
                    name="project",
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="projects.project"),
                ),
                migrations.AlterField(
                    model_name="timeentry",
                    name="task",
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="entries", to="projects.task"),
                ),
                migrations.DeleteModel(name="Project"),
                migrations.DeleteModel(name="Task"),
            ],
            database_operations=[],
        ),
    ]
