"""The personal dashboard (FR-5, D-74–D-80)."""

from django.shortcuts import render
from django.utils import timezone

from analytics.services.metrics import RANGES, dashboard_for, range_weeks


def dashboard(request):
    """FR-5: the logged-in person's own dashboard. No parameter can pick another employee."""
    weeks = range_weeks(request.GET.get("weeks"))
    dash = dashboard_for(request.user.employee, weeks, timezone.now())
    return render(request, "analytics/dashboard.html", {"dash": dash, "ranges": RANGES})
