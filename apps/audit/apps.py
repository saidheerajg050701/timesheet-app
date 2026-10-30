from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "apps.audit"
    label = "audit"  # unchanged: tables, migrations and audit names stay the same (D-174)
