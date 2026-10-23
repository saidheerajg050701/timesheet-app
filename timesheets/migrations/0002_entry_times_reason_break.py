# Phase 5b (D-36, D-37, D-39, D-44): entry times, required reason, Break category.
# Written by hand because makemigrations asks interactively about the notes → reason rename.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("timesheets", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(model_name="timeentry", old_name="notes", new_name="reason"),
        migrations.AlterField(
            model_name="timeentry",
            name="reason",
            field=models.CharField(max_length=255),
        ),
        migrations.AddField(
            model_name="timeentry",
            name="start_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="timeentry",
            name="end_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="timeentry",
            name="category",
            field=models.CharField(
                choices=[
                    ("PROJECT", "Project work"),
                    ("MEETING", "Meetings"),
                    ("TRAINING", "Training"),
                    ("OTHER", "Other"),
                    ("BREAK", "Break time"),
                    ("PTO", "PTO"),
                    ("SICK", "Sick"),
                    ("HOLIDAY", "Holiday"),
                ],
                max_length=10,
            ),
        ),
        migrations.AddConstraint(
            model_name="timeentry",
            constraint=models.CheckConstraint(
                condition=models.Q(("end_time__isnull", True), ("start_time__isnull", True))
                | models.Q(("end_time__isnull", False), ("start_time__isnull", False)),
                name="entry_times_paired",
            ),
        ),
        migrations.AddConstraint(
            model_name="timeentry",
            constraint=models.CheckConstraint(
                condition=models.Q(("start_time__isnull", True))
                | models.Q(("end_time__gt", models.F("start_time"))),
                name="entry_end_after_start",
            ),
        ),
    ]
