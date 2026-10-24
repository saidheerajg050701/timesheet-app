from django.contrib import admin

from directory.admin_base import ViewOnlyAdmin
from payroll.models import PayrollWeek


@admin.register(PayrollWeek)
class PayrollWeekAdmin(ViewOnlyAdmin):
    """Read-only: payroll records change only through the payroll services (D-15, D-67)."""

    list_display = (
        "employee_code",
        "employee_name",
        "week_start",
        "version",
        "status",
        "total_minutes",
        "export_batch",
    )
    list_filter = ("status", "period_start", "department")
    search_fields = ("employee_code", "employee_name", "export_batch")
    ordering = ("-week_start", "employee_code", "-version")
