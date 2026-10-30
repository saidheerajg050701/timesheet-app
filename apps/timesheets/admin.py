from django.contrib import admin

from apps.directory.admin_base import ViewOnlyAdmin, ViewOnlyInline
from apps.timesheets.models import ChangeRequest, PeriodApproval, TimeEntry, Timesheet


class TimeEntryInline(ViewOnlyInline):
    model = TimeEntry
    verbose_name_plural = "time entries"
    fields = (
        "work_date",
        "category",
        "project",
        "task",
        "start_time",
        "end_time",
        "minutes",
        "reason",
    )
    ordering = ("work_date", "start_time")


@admin.register(Timesheet)
class TimesheetAdmin(ViewOnlyAdmin):
    list_display = ("employee", "week_start", "status", "is_late", "submitted_at", "reopen_until")
    list_filter = ("status", "is_late", "week_start", "employee__team")
    search_fields = (
        "employee__employee_code",
        "employee__first_name",
        "employee__last_name",
        "employee__email",
    )
    list_select_related = ("employee",)
    date_hierarchy = "week_start"
    ordering = ("-week_start", "employee__employee_code")
    inlines = (TimeEntryInline,)


@admin.register(PeriodApproval)
class PeriodApprovalAdmin(ViewOnlyAdmin):
    list_display = ("employee", "period_start", "status", "approver", "decided_at")
    list_filter = ("status", "period_start")
    search_fields = ("employee__employee_code", "employee__first_name", "employee__last_name")
    list_select_related = ("employee", "approver")
    ordering = ("-period_start", "employee__employee_code")


@admin.register(ChangeRequest)
class ChangeRequestAdmin(ViewOnlyAdmin):
    list_display = ("pk", "timesheet", "requester", "status", "reviewer", "created_at")
    list_filter = ("status",)
    search_fields = ("requester__employee_code", "reason")
    list_select_related = ("timesheet__employee", "requester", "reviewer")
    ordering = ("-created_at",)
