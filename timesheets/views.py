from django.shortcuts import render

from directory.services.permissions import approvals_required


def placeholder(request, title, phase):
    """A page built in a later phase; its permission is already enforced (D-30)."""
    return render(request, "placeholder.html", {"title": title, "phase": phase})


def timesheet_list(request):
    return placeholder(request, "Timesheets", 5)


def request_list(request):
    return placeholder(request, "Change requests", 6)


@approvals_required
def approval_list(request):
    return placeholder(request, "Approvals", 7)
