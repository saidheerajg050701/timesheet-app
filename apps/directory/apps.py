from django.apps import AppConfig


class DirectoryConfig(AppConfig):
    name = "apps.directory"
    label = "directory"  # unchanged: tables, migrations and audit names stay the same (D-174)

    def ready(self):
        from apps.directory import checks  # noqa: F401 — registers the secret-key check (D-145)
