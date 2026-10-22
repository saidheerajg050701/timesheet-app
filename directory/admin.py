from django.contrib import admin
from django.contrib.auth.hashers import identify_hasher
from django.utils.html import format_html_join

from directory.admin_base import ViewOnlyAdmin
from directory.models import Employee, Team, User


@admin.register(Team)
class TeamAdmin(ViewOnlyAdmin):
    list_display = ("name", "department")
    list_filter = ("department",)
    search_fields = ("name", "department")


@admin.register(Employee)
class EmployeeAdmin(ViewOnlyAdmin):
    list_display = (
        "employee_code",
        "first_name",
        "last_name",
        "email",
        "job_title",
        "team",
        "manager",
        "status",
        "is_admin",
        "is_payroll",
    )
    list_filter = ("status", "team__department", "team", "is_admin", "is_payroll")
    search_fields = ("employee_code", "first_name", "last_name", "email", "job_title")
    list_select_related = ("team", "manager")
    ordering = ("employee_code",)


@admin.register(User)
class UserAdmin(ViewOnlyAdmin):
    list_display = ("email", "employee", "is_active", "is_staff", "last_login")
    list_filter = ("is_active", "is_staff")
    search_fields = ("email", "employee__employee_code")
    list_select_related = ("employee",)
    ordering = ("email",)
    fields = (
        "email",
        "employee",
        "password_summary",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
        "date_joined",
    )
    readonly_fields = ("password_summary",)

    @admin.display(description="Password")
    def password_summary(self, obj):
        """Algorithm and parameters only; salt and hash are masked, never shown in full."""
        try:
            hasher = identify_hasher(obj.password)
        except ValueError:
            return "No usable password"
        return format_html_join(", ", "{}: {}", hasher.safe_summary(obj.password).items())
