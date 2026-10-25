from django.apps import AppConfig


class TimesheetsConfig(AppConfig):
    name = "timesheets"

    def ready(self):
        from timesheets import checks  # noqa: F401  registers the pay-period anchor check (D-113)
