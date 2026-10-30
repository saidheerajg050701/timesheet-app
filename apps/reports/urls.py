"""Reports → Project hours and Project budget (D-160, D-170): the same addresses as before
Refactor R2 (D-174)."""

from django.urls import path

from apps.reports import views as reports

urlpatterns = [
    path("reports/project-hours/", reports.project_hours, name="project_hours"),
    path("reports/project-hours/excel/", reports.project_hours_xlsx, name="project_hours_xlsx"),
    path("reports/project-hours/csv/", reports.project_hours_csv, name="project_hours_csv"),
    path("reports/projects/", reports.report_projects, name="report_projects"),
    path("reports/project-budget/", reports.project_budget, name="project_budget"),
    path(
        "reports/project-budget/excel/",
        reports.project_budget_xlsx,
        name="project_budget_xlsx",
    ),
    path("reports/project-budget/csv/", reports.project_budget_csv, name="project_budget_csv"),
]
