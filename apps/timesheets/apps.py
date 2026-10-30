from django.apps import AppConfig


class TimesheetsConfig(AppConfig):
    name = "apps.timesheets"
    label = "timesheets"  # unchanged: tables, migrations and audit names stay the same (D-174)

    def ready(self):
        from apps.timesheets import checks  # noqa: F401  registers the pay-period anchor check (D-113)
