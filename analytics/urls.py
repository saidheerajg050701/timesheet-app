from django.urls import path

from analytics import views

urlpatterns = [
    path("team/", views.team, name="team"),
    path("team/<str:employee_code>/", views.team_member, name="team_member"),
]
