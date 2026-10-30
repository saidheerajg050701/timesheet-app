from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    name = "apps.analytics"
    label = "analytics"  # unchanged: tables, migrations and audit names stay the same (D-174)
