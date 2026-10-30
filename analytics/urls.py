from django.urls import path

from analytics.views import dashboard, reports, team

urlpatterns = [
    path("", dashboard.dashboard, name="home"),  # replaces the placeholder (D-30)
    path("team/", team.team, name="team"),
    path("team/<str:employee_code>/", team.team_member, name="team_member"),
    path(
        "team/<str:employee_code>/weeks/<isodate:week>/",
        team.team_member_week,
        name="team_member_week",
    ),
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
