# Change 10 (D-148, D-149): the 9 default tasks, and every existing project allows all of them.
# Existing time entries are never touched: their task stays empty ("Task not recorded", D-151).

from django.db import migrations

DEFAULT_TASKS = (  # (code, name, description) — sorted 10, 20, … in this order
    ("PLN", "Planning & Analysis", "Discovery, requirements, estimates, project management"),
    ("DES", "Design & Architecture", "UX/UI and technical design"),
    ("DEV", "Development", "Features, code review, refactoring and tech debt"),
    ("TST", "Testing & QA", ""),
    ("REL", "Release & DevOps", "Builds, deployments, production releases"),
    ("SUP", "Support & Bug Fixes", ""),
    ("SEC", "Security & Compliance", ""),
    ("DOC", "Documentation & Knowledge Transfer", ""),
    ("MTG", "Project Meetings & Coordination", "Meetings for this project"),
)


def add_default_tasks(apps, schema_editor):
    Task = apps.get_model("timesheets", "Task")
    Project = apps.get_model("timesheets", "Project")
    tasks = []
    for number, (code, name, description) in enumerate(DEFAULT_TASKS, start=1):
        task, _ = Task.objects.get_or_create(
            code=code,
            defaults={"name": name, "description": description, "sort_order": number * 10},
        )
        tasks.append(task)
    for project in Project.objects.all():
        project.tasks.add(*tasks)


class Migration(migrations.Migration):

    dependencies = [
        ("timesheets", "0006_tasks"),
    ]

    operations = [
        migrations.RunPython(add_default_tasks, migrations.RunPython.noop),
    ]
