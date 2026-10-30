from django.apps import AppConfig


class PayrollConfig(AppConfig):
    name = "apps.payroll"
    label = "payroll"  # unchanged: tables, migrations and audit names stay the same (D-174)
