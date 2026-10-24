from django.urls import path

from analytics import views

urlpatterns = [
    path("", views.dashboard, name="home"),  # replaces the placeholder (D-30)
    path("team/", views.team, name="team"),
    path("team/<str:employee_code>/", views.team_member, name="team_member"),
    path(
        "team/<str:employee_code>/weeks/<isodate:week>/",
        views.team_member_week,
        name="team_member_week",
    ),
]
