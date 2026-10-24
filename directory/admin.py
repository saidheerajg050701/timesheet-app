from decimal import Decimal

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import RelatedOnlyFieldListFilter
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.hashers import identify_hasher
from django.core import signing
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html_join

from directory.admin_base import AuditedAdmin, ViewOnlyAdmin
from directory.models import Employee, Team, User
from directory.services import directory_admin
from directory.services.importer import EmployeeImportError, import_employees, read_csv

IMPORT_SALT = "employee-csv-import"
IMPORT_MAX_BYTES = 1024 * 1024  # 1 MB (D-92)
IMPORT_MAX_AGE = 60 * 60  # a preview can be confirmed for an hour


@admin.register(Team)
class TeamAdmin(AuditedAdmin):
    list_display = ("name", "department")
    list_filter = ("department",)
    search_fields = ("name", "department")
    save_service = staticmethod(directory_admin.save_team)


class EmployeeForm(forms.ModelForm):
    """Expected hours are typed as hours (e.g. 37.5) and stored as minutes (D-87)."""

    expected_weekly_hours = forms.DecimalField(
        min_value=Decimal("0.25"),
        max_value=Decimal("80"),
        decimal_places=2,
        step_size=Decimal("0.25"),
        help_text="Hours per week, in quarter hours (40 = full time).",
    )

    class Meta:
        model = Employee
        fields = (
            "employee_code",
            "first_name",
            "last_name",
            "email",
            "job_title",
            "team",
            "manager",
            "location",
            "hire_date",
            "expected_weekly_hours",
            "is_admin",
            "is_payroll",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        minutes = self.instance.expected_weekly_minutes
        self.fields["expected_weekly_hours"].initial = Decimal(minutes) / 60

    def clean_employee_code(self):
        return self.cleaned_data["employee_code"].strip().upper()

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def _post_clean(self):
        super()._post_clean()
        hours = self.cleaned_data.get("expected_weekly_hours")
        if hours is not None:
            self.instance.expected_weekly_minutes = int(hours * 60)


class DeactivateForm(forms.Form):
    end_date = forms.DateField(
        label="End date (last working day)",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Today or earlier; not before the hire date or the last saved time entry.",
    )


class ImportForm(forms.Form):
    file = forms.FileField(label="CSV file", help_text="Same columns as Export CSV. Max 1 MB.")

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > IMPORT_MAX_BYTES:
            raise ValidationError("The file is larger than 1 MB.")
        try:
            return upload.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValidationError("Save the file as CSV UTF-8 and try again.") from None


@admin.register(Employee)
class EmployeeAdmin(AuditedAdmin):
    form = EmployeeForm
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
    list_filter = (
        "status",
        "team__department",
        "team",
        "is_admin",
        "is_payroll",
        ("manager", RelatedOnlyFieldListFilter),
    )
    search_fields = (
        "employee_code",
        "first_name",
        "last_name",
        "email",
        "job_title",
        "team__name",
        "team__department",
        "manager__first_name",
        "manager__last_name",
        "manager__employee_code",
    )
    list_select_related = ("team", "manager")
    autocomplete_fields = ("team", "manager")
    ordering = ("employee_code",)
    actions = ("deactivate", "reactivate")
    save_service = staticmethod(directory_admin.save_employee)
    check_service = staticmethod(directory_admin.check_employee)

    def get_readonly_fields(self, request, obj=None):
        fixed = ("status", "end_date")  # changed only by Deactivate / Reactivate (D-90)
        return ("employee_code", *fixed) if obj else fixed

    def get_urls(self):
        view = self.admin_site.admin_view
        return [
            path("import/", view(self.import_view), name="directory_employee_import"),
            path("export/", view(self.export_view), name="directory_employee_export"),
            path(
                "<int:pk>/reset-password/",
                view(self.reset_password_view),
                name="directory_employee_reset_password",
            ),
            *super().get_urls(),
        ]

    def page(self, request, template, title, **context):
        return TemplateResponse(
            request,
            f"admin/directory/employee/{template}",
            {**self.admin_site.each_context(request), "opts": self.opts, "title": title, **context},
        )

    # --- deactivate / reactivate (D-90) ---------------------------------------------------

    @admin.action(description="Deactivate selected employees")
    def deactivate(self, request, queryset):
        form = DeactivateForm(
            request.POST if "apply" in request.POST else None,
            initial={"end_date": timezone.localdate()},
        )
        if form.is_valid():
            try:
                count = directory_admin.deactivate(
                    request.user.employee, queryset, form.cleaned_data["end_date"]
                )
            except ValidationError as exc:
                for message in exc.messages:
                    self.message_user(request, message, messages.ERROR)
                self.message_user(request, "Nobody was deactivated.", messages.ERROR)
                return None
            self.message_user(request, f"Deactivated {count} employee(s).", messages.SUCCESS)
            return None
        return self.page(
            request,
            "deactivate.html",
            "Deactivate employees",
            form=form,
            employees=queryset,
            action_checkbox_name=ACTION_CHECKBOX_NAME,
        )

    @admin.action(description="Reactivate selected employees")
    def reactivate(self, request, queryset):
        try:
            count = directory_admin.reactivate(request.user.employee, queryset)
        except ValidationError as exc:
            for message in exc.messages:
                self.message_user(request, message, messages.ERROR)
            return
        self.message_user(request, f"Reactivated {count} employee(s).", messages.SUCCESS)

    # --- password reset (D-91) ------------------------------------------------------------

    def reset_password_view(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        user = User.objects.filter(employee=employee).first()
        form = SetPasswordForm(user, request.POST or None) if user else None
        if form is not None:
            form.fields["new_password1"].label = "Temporary password"
            form.fields["new_password2"].label = "Temporary password (again)"
        if request.method == "POST" and form is not None and form.is_valid():
            try:
                directory_admin.reset_password(
                    request.user.employee, employee, form.cleaned_data["new_password1"]
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                self.message_user(
                    request,
                    f"Temporary password set for {employee}. They must choose a new one at "
                    "their next login; any lockout was cleared.",
                    messages.SUCCESS,
                )
                return redirect("admin:directory_employee_change", employee.pk)
        return self.page(
            request,
            "reset_password.html",
            f"Reset password: {employee}",
            employee=employee,
            form=form,
            own=employee.pk == request.user.employee.pk,
        )

    # --- CSV import / export (D-92) -------------------------------------------------------

    def import_view(self, request):
        actor = request.user.employee
        if "confirm" in request.POST:
            try:
                text = signing.loads(
                    request.POST["payload"], salt=IMPORT_SALT, max_age=IMPORT_MAX_AGE
                )
            except signing.BadSignature:
                self.message_user(
                    request, "The preview expired; upload the file again.", messages.ERROR
                )
                return redirect("admin:directory_employee_import")
            columns, rows = read_csv(text)
            try:
                result = import_employees(rows, columns=columns, actor=actor)
            except EmployeeImportError as exc:
                return self.page(
                    request, "import.html", "Import employees", form=ImportForm(), errors=exc.errors
                )
            self.message_user(
                request,
                f"Imported: {result.created} created, {result.updated} updated, "
                f"{result.unchanged} unchanged, {result.teams_created} new team(s).",
                messages.SUCCESS,
            )
            return redirect("admin:directory_employee_changelist")
        form = ImportForm(request.POST or None, request.FILES or None)
        context = {"form": form}
        if request.method == "POST" and form.is_valid():
            text = form.cleaned_data["file"]
            columns, rows = read_csv(text)
            try:
                preview = import_employees(rows, columns=columns, actor=actor, dry_run=True)
            except EmployeeImportError as exc:
                context["errors"] = exc.errors
            else:
                context["preview"] = preview
                context["payload"] = signing.dumps(text, salt=IMPORT_SALT, compress=True)
        return self.page(request, "import.html", "Import employees", **context)

    def export_view(self, request):
        """The employees in the current list filters, as CSV."""
        queryset = self.get_changelist_instance(request).get_queryset(request)
        text = directory_admin.export_employees(request.user.employee, queryset)
        response = HttpResponse("﻿" + text, content_type="text/csv; charset=utf-8")
        stamp = timezone.localdate().isoformat()
        response["Content-Disposition"] = f'attachment; filename="employees-{stamp}.csv"'
        return response

    def changelist_view(self, request, extra_context=None):
        extra = {
            "export_url": reverse("admin:directory_employee_export") + "?" + request.GET.urlencode()
        }
        return super().changelist_view(request, {**extra, **(extra_context or {})})


@admin.register(User)
class UserAdmin(ViewOnlyAdmin):
    list_display = (
        "email",
        "employee",
        "is_active",
        "is_staff",
        "must_change_password",
        "last_login",
    )
    list_filter = ("is_active", "is_staff", "must_change_password")
    search_fields = ("email", "employee__employee_code")
    list_select_related = ("employee",)
    ordering = ("email",)
    fields = (
        "email",
        "employee",
        "password_summary",
        "must_change_password",
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
