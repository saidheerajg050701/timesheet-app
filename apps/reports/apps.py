from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Reports → Project hours and Project budget, with their Excel and CSV downloads (D-160–D-171,
    D-174). No models."""

    name = "apps.reports"
    label = "reports"
