# Change 10b (D-155, D-156): project codes become I-001, I-002, … with a stored number.
# PRJ-<number> keeps its number when that I-number is free; any other code (or a number
# already taken) gets the next free number after the highest, in code order. Time entries and
# allowed tasks link to projects by id, so they don't change; audit rows are never edited.

import re

from django.db import migrations, models

PRJ = re.compile(r"^PRJ-(\d+)$")


def i_code(number):
    return f"I-{number:03d}"


def to_i_codes(apps, schema_editor):
    Project = apps.get_model("timesheets", "Project")
    projects = list(Project.objects.order_by("code"))
    taken, later = set(), []
    for project in projects:
        match = PRJ.match(project.code)
        number = int(match[1]) if match else 0
        if number and number not in taken:
            taken.add(number)
            project.number = number
        else:
            later.append(project)
    for project in later:  # in code order, after the highest number
        project.number = max(taken, default=0) + 1
        taken.add(project.number)
    renames = [(project.code, i_code(project.number), project) for project in projects]
    for _, new, project in renames:  # temporary codes first, so no two projects ever clash
        project.code = f"~{project.pk}"
        project.save(update_fields=["code", "number"])
    for old, new, project in renames:
        project.code = new
        project.save(update_fields=["code"])
        print(f"\n  Project {old} → {new}", end="")


def to_prj_codes(apps, schema_editor):
    """Best effort: back to PRJ-<number> (other old codes are not kept, D-156)."""
    Project = apps.get_model("timesheets", "Project")
    for project in Project.objects.all():
        project.code = f"PRJ-{project.number:03d}"
        project.save(update_fields=["code"])


class Migration(migrations.Migration):

    dependencies = [
        ("timesheets", "0007_default_tasks"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="number",
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.RunPython(to_i_codes, to_prj_codes),
        migrations.AlterField(
            model_name="project",
            name="number",
            field=models.PositiveIntegerField(unique=True),
        ),
        migrations.AlterModelOptions(
            name="project",
            options={"ordering": ("number",)},
        ),
    ]
