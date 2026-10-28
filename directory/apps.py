from django.apps import AppConfig


class DirectoryConfig(AppConfig):
    name = "directory"

    def ready(self):
        from directory import checks  # noqa: F401 — registers the secret-key check (D-145)
