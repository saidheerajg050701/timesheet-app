"""Reports → Project hours (Change 11, D-160–D-164). Views stay thin: every number comes from
analytics/services/project_report.py, the files from report_files.py. Who may see whom is
checked there on every request (page, filters and downloads): 403 for anything else."""

from urllib.parse import urlencode

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from analytics.services.project_report import (
    FOOTNOTE,
    GROUPS,
    HOURS,
    PERIODS,
    SCOPES,
    project_report,
)
from analytics.services.report_files import audit_download, detail_csv, file_name, workbook
from timesheets.services.projects import search_projects

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
        "analytics/project_hours.html",
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
        "timesheets/_project_options.html",
        {"groups": [(h, p) for h, p in groups if p], "show_inactive": True},
    )
