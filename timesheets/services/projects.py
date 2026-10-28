"""Project I-codes and project search (Change 10b, D-155–D-158): the one place for both.

A project's code is "I-" and its number with at least 3 digits (I-001 … I-999, I-1000). The
app assigns it when a project is added: the next number after the highest ever used. Projects
are never deleted (D-87), so the highest existing number is the highest ever used — numbers
are never reused, and codes are never edited.
"""

from datetime import timedelta

from django.db.models import Max, Q

from timesheets.models import Project, TimeEntry

RECENT_WEEKS = 4  # "Your recent projects": the 4 weeks before the week being edited (D-158)


def format_code(number):
    """7 → "I-007"; 1000 → "I-1000"."""
    return f"I-{number:03d}"


def next_number():
    return (Project.objects.aggregate(top=Max("number"))["top"] or 0) + 1


def assign_code(project):
    """Give a new project the next number and its I-code (call inside the saving transaction;
    the unique number and code refuse a duplicate)."""
    project.number = next_number()
    project.code = format_code(project.number)
    return project


def search_projects(text):
    """Active projects whose I-code or name contains `text` — partial, any case ("i-00", "001",
    "portal"); all active projects for an empty text. Sorted by I-code (D-157)."""
    text = (text or "").strip()
    projects = Project.objects.filter(active=True)
    if text:
        projects = projects.filter(Q(code__icontains=text) | Q(name__icontains=text))
    return list(projects.order_by("number"))


def recent_projects(employee, week_start):
    """The active projects `employee` booked work to in the 4 weeks before `week_start`,
    sorted by I-code (D-158)."""
    entries = TimeEntry.objects.filter(
        timesheet__employee=employee,
        work_date__gte=week_start - timedelta(weeks=RECENT_WEEKS),
        work_date__lt=week_start,
        project__isnull=False,
    )
    ids = entries.values("project_id")
    return list(Project.objects.filter(active=True, pk__in=ids).order_by("number"))


def project_options(text, employee, week_start):
    """What the project search box lists (D-157, D-158): [(heading, [projects])].

    Empty box: "Your recent projects", then "All active projects" (the others). Typing:
    "Matching projects" — empty when nothing matches ("No matching project").
    """
    if (text or "").strip():
        groups = [("Matching projects", search_projects(text))]
    else:
        recent = recent_projects(employee, week_start)
        others = [p for p in search_projects("") if p not in recent]
        groups = [("Your recent projects", recent), ("All active projects", others)]
    return [(heading, projects) for heading, projects in groups if projects]
