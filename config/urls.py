from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Public placeholder until Phase 3 (login) and Phase 9 (dashboard). Shows no data.
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
]
