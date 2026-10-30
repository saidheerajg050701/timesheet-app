from django.urls import path

from apps.analytics.views import dashboard, team

urlpatterns = [
    path("", dashboard.dashboard, name="home"),  # replaces the placeholder (D-30)
    path("team/", team.team, name="team"),
    path("team/<str:employee_code>/", team.team_member, name="team_member"),
    path(
        "team/<str:employee_code>/weeks/<isodate:week>/",
        team.team_member_week,
        name="team_member_week",
    ),
]
