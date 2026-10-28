from django import forms
from django.contrib import admin, messages

from directory.admin_base import AuditedAdmin, ViewOnlyAdmin, ViewOnlyInline
from directory.services.directory_admin import save_project, save_task, set_project_tasks
from timesheets.models import ChangeRequest, PeriodApproval, Project, Task, TimeEntry, Timesheet
from timesheets.services.tasks import active_tasks

OPEN_WEEKS_NOTE = "open weeks must choose another task when they are saved again."


def saved_entries(count):
    return f"{count} saved {'entry' if count == 1 else 'entries'}"


@admin.register(Task)
class TaskAdmin(AuditedAdmin):
    """Add and edit (audited, D-148); retire a task by clearing Active, never delete."""

    list_display = ("code", "name", "active", "sort_order")
    list_filter = ("active",)
    search_fields = ("code", "name")
    save_service = staticmethod(save_task)

    def get_fields(self, request, obj=None):
        fields = ("code", "name", "description", "active", "sort_order")
        return (*fields, "usage") if obj else fields

    def get_readonly_fields(self, request, obj=None):
        return ("code", "usage") if obj else ()  # entries and audit rows refer to the code

    @admin.display(description="Used by")
    def usage(self, task):
        return f"{saved_entries(task.entries.count())} (history keeps this task)"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        used = obj.entries.count()
        if change and "active" in form.changed_data and not obj.active and used:
            note = f"{obj.code} is used by {saved_entries(used)}; {OPEN_WEEKS_NOTE}"
            messages.info(request, note)


@admin.register(Project)
class ProjectAdmin(AuditedAdmin):
    """Add and edit (audited, D-88); retire a project by clearing Active, never delete.
    "Allowed tasks" is ticked here; a new project starts with every active task (D-149)."""

    list_display = ("code", "name", "active")
    list_filter = ("active",)
    search_fields = ("code", "name")
    ordering = ("number",)
    save_service = staticmethod(save_project)

    def get_fields(self, request, obj=None):
        """The I-code is assigned when a project is added and never edited (D-155)."""
        return ("code", "name", "active", "tasks") if obj else ("name", "active", "tasks")

    def get_readonly_fields(self, request, obj=None):
        return ("code",) if obj else ()  # entries and audit rows refer to the code

    def render_change_form(self, request, context, add=False, **kwargs):
        if add:
            context["subtitle"] = "The I-code (I-001, I-002, …) is assigned when you save."
        return super().render_change_form(request, context, add=add, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "tasks":
            kwargs.update(widget=forms.CheckboxSelectMultiple, label="Allowed tasks")
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        return {"tasks": list(active_tasks()), **super().get_changeform_initial_data(request)}

    def save_related(self, request, form, formsets, change):
        """The task list goes through the audited service instead of form.save_m2m()."""
        project = form.instance
        in_use = set_project_tasks(request.user.employee, project, form.cleaned_data["tasks"])
        for task, count in in_use.items():
            used = f"{saved_entries(count)} of {project.code}"
            note = f"{task.code} is used by {used}; {OPEN_WEEKS_NOTE}"
            messages.info(request, note)
        for formset in formsets:
            self.save_formset(request, form, formset, change=change)


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
