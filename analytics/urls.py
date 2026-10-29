from django.urls import path

from analytics import report_views, views

urlpatterns = [
    path("", views.dashboard, name="home"),  # replaces the placeholder (D-30)
    path("team/", views.team, name="team"),
    path("team/<str:employee_code>/", views.team_member, name="team_member"),
    path(
        "team/<str:employee_code>/weeks/<isodate:week>/",
        views.team_member_week,
        name="team_member_week",
    ),
    path("reports/project-hours/", report_views.project_hours, name="project_hours"),
    path(
        "reports/project-hours/excel/", report_views.project_hours_xlsx, name="project_hours_xlsx"
    ),
    path("reports/project-hours/csv/", report_views.project_hours_csv, name="project_hours_csv"),
    path("reports/projects/", report_views.report_projects, name="report_projects"),
    path("reports/project-budget/", report_views.project_budget, name="project_budget"),
    path(
        "reports/project-budget/excel/",
        report_views.project_budget_xlsx,
        name="project_budget_xlsx",
    ),
    path("reports/project-budget/csv/", report_views.project_budget_csv, name="project_budget_csv"),
]
