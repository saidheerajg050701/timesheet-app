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
from django.utils.html import format_html, format_html_join

from directory.admin_base import AuditedAdmin, ViewOnlyAdmin
from directory.models import Employee, PayRecord, Team, User
from directory.services import directory_admin
from directory.services.importer import EmployeeImportError, import_employees, read_csv
from directory.services.pay import (
    add_pay,
    check_pay,
    current_pay,
    history,
    money,
)
from directory.services.pay_import import PAY_COLUMNS, PayImportError, export_pay, import_pay
from directory.services.permissions import can_manage_pay, ensure

IMPORT_SALT = "employee-csv-import"
IMPORT_MAX_BYTES = 1024 * 1024  # 1 MB (D-92)
IMPORT_MAX_AGE = 60 * 60  # a preview can be confirmed for an hour
PAY_IMPORT_SALT = "pay-csv-import"


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


class PayForm(forms.Form):
    """Add pay change (D-166): amounts as text so "$85,000" works; checked by pay.py."""

    pay_type = forms.ChoiceField(choices=PayRecord.PayType.choices, widget=forms.RadioSelect)
    annual_salary = forms.CharField(
        required=False, label="Annual salary (USD)", help_text="Salaried only."
    )
    hourly_rate = forms.CharField(
        required=False,
        label="Hourly rate (USD)",
        help_text="Salaried: suggested = annual salary ÷ 2,080 (40 h × 52 weeks); leave empty "
        "to use the suggestion, or type your own. Hourly: required.",
    )
    effective_from = forms.DateField(
        label="Effective from",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="The first day this pay applies. A date in the past re-prices project work "
        "from that day; the same date as an earlier record corrects it (newer wins).",
    )

    def __init__(self, employee, *args, **kwargs):
        self.employee = employee
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        for name in ("annual_salary", "hourly_rate"):
            try:
                data[name] = money(data.get(name))
            except ValueError:
                self.add_error(name, "Type an amount such as 85000 or 41.25.")
        if not self.errors:
            found = check_pay(
                self.employee,
                data.get("pay_type"),
                data.get("annual_salary"),
                data.get("hourly_rate"),
                data.get("effective_from"),
            )
            for field_name, messages_ in found.items():
                self.add_error(field_name, messages_)
        return data


class PayImportForm(ImportForm):
    pass


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
        return ("employee_code", *fixed, "pay") if obj else fixed

    @admin.display(description="Pay")
    def pay(self, employee):
        """The pay in force today and a link to the history (admins only, D-167)."""
        link = reverse("admin:directory_employee_pay", args=[employee.pk])
        pay = current_pay(employee, timezone.localdate())
        if pay is None:
            summary = "No pay record yet — project hours are not costed (Rate missing)."
        else:
            salary = f", ${pay.annual_salary:,.2f} a year" if pay.annual_salary is not None else ""
            summary = (
                f"{pay.get_pay_type_display()}: ${pay.hourly_rate:,.2f} an hour{salary} "
                f"(since {pay.effective_from:%b %-d, %Y})."
            )
        return format_html(
            '{} <a href="{}" id="pay-history">Pay history and changes</a>', summary, link
        )

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
            path("<int:pk>/pay/", view(self.pay_view), name="directory_employee_pay"),
            path("pay-import/", view(self.pay_import_view), name="directory_employee_pay_import"),
            path("pay-export/", view(self.pay_export_view), name="directory_employee_pay_export"),
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

    # --- pay (Change 12, D-166, D-167): admins only, history only ever grows ----------------

    def pay_view(self, request, pk):
        ensure(can_manage_pay(request.user.employee))
        employee = get_object_or_404(Employee, pk=pk)
        form = PayForm(employee, request.POST or None)
        if request.method == "POST" and form.is_valid():
            data = form.cleaned_data
            add_pay(
                request.user.employee,
                employee,
                data["pay_type"],
                data["annual_salary"],
                data["hourly_rate"],
                data["effective_from"],
                today=timezone.localdate(),
            )
            self.message_user(request, f"Pay change saved for {employee}.", messages.SUCCESS)
            return redirect("admin:directory_employee_pay", employee.pk)
        return self.page(
            request,
            "pay.html",
            f"Pay: {employee}",
            employee=employee,
            form=form,
            current=current_pay(employee, timezone.localdate()),
            history=history(employee),
            year_hours=2080,
        )

    def pay_export_view(self, request):
        ensure(can_manage_pay(request.user.employee))
        text = export_pay(request.user.employee)
        response = HttpResponse("\ufeff" + text, content_type="text/csv; charset=utf-8")
        stamp = timezone.localdate().isoformat()
        response["Content-Disposition"] = f'attachment; filename="pay-{stamp}.csv"'
        return response

    def pay_import_view(self, request):
        ensure(can_manage_pay(request.user.employee))
        actor = request.user.employee
        title = "Import pay"
        if "confirm" in request.POST:
            try:
                text = signing.loads(
                    request.POST["payload"], salt=PAY_IMPORT_SALT, max_age=IMPORT_MAX_AGE
                )
            except signing.BadSignature:
                self.message_user(
                    request, "The preview expired; upload the file again.", messages.ERROR
                )
                return redirect("admin:directory_employee_pay_import")
            columns, rows = read_csv(text)
            try:
                result = import_pay(rows, columns=columns, actor=actor)
            except PayImportError as exc:
                context = {"form": PayImportForm(), "errors": exc.errors, "columns": PAY_COLUMNS}
                return self.page(request, "pay_import.html", title, **context)
            self.message_user(
                request,
                f"Pay imported: {result.added} added ({result.corrections} correction(s)), "
                f"{result.unchanged} unchanged.",
                messages.SUCCESS,
            )
            return redirect("admin:directory_employee_changelist")
        form = PayImportForm(request.POST or None, request.FILES or None)
        context = {"form": form, "columns": PAY_COLUMNS}
        if request.method == "POST" and form.is_valid():
            text = form.cleaned_data["file"]
            columns, rows = read_csv(text)
            try:
                context["preview"] = import_pay(rows, columns=columns, actor=actor, dry_run=True)
            except PayImportError as exc:
                context["errors"] = exc.errors
            else:
                context["payload"] = signing.dumps(text, salt=PAY_IMPORT_SALT, compress=True)
        return self.page(request, "pay_import.html", title, **context)

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
