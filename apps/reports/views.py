"""Reports → Project hours (Change 11, D-160–D-164). Views stay thin: every number comes from
apps/reports/services/project_report/, the files from report_files.py. Who may see whom is
checked there on every request (page, filters and downloads): 403 for anything else."""

from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.projects.services.projects import search_projects
from apps.reports.services import cost_files
from apps.reports.services.project_costs import NOTES, project_costs
from apps.reports.services.project_report import (
    FOOTNOTE,
    GROUPS,
    HOURS,
    PERIODS,
    SCOPES,
    project_report,
)
from apps.reports.services.report_files import audit_download, detail_csv, file_name, workbook

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _report(request):
    return project_report(request.user.employee, request.GET, timezone.now())


def _url(name, report, **changes):
    """This report's address with some filters changed (links, drill-down, downloads)."""
    query = report.filters.query(not report.own)
    query.update(changes)
    params = [
        (k, v)
        for k, value in query.items()
        for v in (value if isinstance(value, list) else [value])
    ]
    return f"{reverse(name)}?{urlencode(params)}"


@require_GET
def project_hours(request):
    report = _report(request)
    for row in report.by_manager:  # each manager drills into their own group (D-162)
        if row.employee is not None:
            code = row.employee.employee_code
            row.drill_url = _url("project_hours", report, scope="manager", manager=code)
    return render(
        request,
        "reports/project_hours.html",
        {
            "report": report,
            "f": report.filters,
            "periods": PERIODS,
            "hours_choices": {k: label for k, (label, _) in HOURS.items()},
            "scopes": SCOPES,
            "groups": GROUPS,
            "xlsx_url": _url("project_hours_xlsx", report),
            "csv_url": _url("project_hours_csv", report),
            "chart": report.chart_data,
            "described": report.filters.described(not report.own),
            "footnote": FOOTNOTE,
        },
    )


@require_GET
def project_hours_xlsx(request):
    report = _report(request)
    response = HttpResponse(workbook(report), content_type=XLSX)
    response["Content-Disposition"] = f'attachment; filename="{file_name(report, "xlsx")}"'
    audit_download(report, "xlsx", len(report.detail))
    return response


@require_GET
def project_hours_csv(request):
    report = _report(request)
    response = HttpResponse("﻿" + detail_csv(report), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{file_name(report, "csv")}"'
    audit_download(report, "csv", len(report.detail))
    return response


@require_GET
def report_projects(request):
    """The report's project search list: every project, inactive ones too (D-161). Projects
    are not personal data; whose hours are counted is decided by the report itself."""
    projects = search_projects(request.GET.get("q", ""), include_inactive=True)
    groups = [
        ("Matching projects" if request.GET.get("q", "").strip() else "All projects", projects)
    ]
    return render(
        request,
        "projects/_project_options.html",
        {"groups": [(h, p) for h, p in groups if p], "show_inactive": True},
    )


# --- Reports → Project budget (Change 12, D-169–D-171) -------------------------------------


def _costs(request):
    """The cost report; 403 for anyone who isn't a manager, payroll or an admin (D-170)."""
    return project_costs(request.user.employee, request.GET, timezone.now())


def _budget_url(name, report, **changes):
    query = report.filters.query(True)
    query.pop("hours", None)  # money is always approved hours: no Hours filter here
    query.update(changes)
    params = [
        (k, v)
        for k, value in query.items()
        for v in (value if isinstance(value, list) else [value])
    ]
    return f"{reverse(name)}?{urlencode(params)}"


@require_GET
def project_budget(request):
    report = _costs(request)
    for row in report.by_manager:  # each manager drills into their own group (D-162)
        if row.employee is not None:
            code = row.employee.employee_code
            row.drill_url = _budget_url("project_budget", report, scope="manager", manager=code)
    hours_report = report.hours
    # The hours report covers the same people for managers and admins; payroll staff who
    # manage nobody see only their own hours there (D-160), so they get no hours link.
    same_people = hours_report.viewer.is_admin or any(
        m == hours_report.viewer.pk for m in hours_report.managers.values()
    )
    return render(
        request,
        "reports/project_budget.html",
        {
            "report": report,
            "f": report.filters,
            "periods": PERIODS,
            "scopes": SCOPES,
            "groups": GROUPS,
            "notes": NOTES,
            "described": [(k, v) for k, v in report.filters.described(True) if k != "Hours"],
            "xlsx_url": _budget_url("project_budget_xlsx", report),
            "csv_url": _budget_url("project_budget_csv", report),
            "hours_xlsx_url": _url("project_hours_xlsx", hours_report) if same_people else "",
            "hours_csv_url": _url("project_hours_csv", hours_report) if same_people else "",
            "hours_page_url": _url("project_hours", hours_report) if same_people else "",
            "chart": report.chart_data,
            "breakdowns": [
                ("By task", "by-task", report.by_task),
                ("By pay type", "by-pay-type", report.by_pay_type),
                ("By pay period", "by-pay-period", report.by_pay_period),
            ],
            "employees": [
                (p, *report.pay_used.get(p.employee.pk, ([], []))) for p in report.people
            ],
            "at_risk": settings.BUDGET_AT_RISK_PERCENT,
            "over": settings.BUDGET_OVER_PERCENT,
        },
    )


@require_GET
def project_budget_xlsx(request):
    report = _costs(request)
    response = HttpResponse(cost_files.workbook(report), content_type=XLSX)
    response["Content-Disposition"] = (
        f'attachment; filename="{cost_files.file_name(report, "xlsx")}"'
    )
    cost_files.audit_download(report, "xlsx", len(report.rows))
    return response


@require_GET
def project_budget_csv(request):
    report = _costs(request)
    text = "\ufeff" + cost_files.detail_csv(report)
    response = HttpResponse(text, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{cost_files.file_name(report, "csv")}"'
    )
    cost_files.audit_download(report, "csv", len(report.rows))
    return response
