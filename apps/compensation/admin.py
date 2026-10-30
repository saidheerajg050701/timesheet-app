"""Employee pay in Admin (D-166, D-167): the Pay page with its history and Add pay change, and
the Pay CSV import/export — admins only. Moved from the directory app in Refactor R2 (D-174):
the Employee admin uses PayAdminMixin, so the pages keep their addresses and URL names
(admin:directory_employee_pay, …_pay_import, …_pay_export)."""

from django import forms
from django.contrib import admin, messages
from django.core import signing
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.compensation.models import PayRecord
from apps.compensation.services.access import can_manage_pay
from apps.compensation.services.pay import (
    add_pay,
    check_pay,
    current_pay,
    history,
    money,
)
from apps.compensation.services.pay_import import (
    PAY_COLUMNS,
    PayImportError,
    export_pay,
    import_pay,
)
from apps.directory.forms import ImportForm
from apps.directory.models import Employee
from apps.directory.services.importer import read_csv
from apps.directory.services.permissions import ensure

PAY_IMPORT_SALT = "pay-csv-import"
IMPORT_MAX_AGE = 60 * 60  # a preview can be confirmed for an hour (as the employee import)


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


class PayAdminMixin:
    """The Pay pages of the Employee admin (D-167): the "Pay" line on an employee, the pay
    history page and the Pay CSV. Used by apps.directory.admin.EmployeeAdmin."""

    def pay_urls(self, view):
        return [
            path("<int:pk>/pay/", view(self.pay_view), name="directory_employee_pay"),
            path("pay-import/", view(self.pay_import_view), name="directory_employee_pay_import"),
            path("pay-export/", view(self.pay_export_view), name="directory_employee_pay_export"),
        ]

    def pay_page(self, request, template, title, **context):
        return TemplateResponse(
            request,
            f"admin/compensation/{template}",
            {**self.admin_site.each_context(request), "opts": self.opts, "title": title, **context},
        )

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
        return self.pay_page(
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
                return self.pay_page(request, "pay_import.html", title, **context)
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
        return self.pay_page(request, "pay_import.html", title, **context)
