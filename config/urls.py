from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from directory.views import admin_login

urlpatterns = [
    path("admin/login/", admin_login),  # one login page for the whole app
    path("admin/", admin.site.urls),
    path("", include("directory.urls")),
    # Placeholder behind login (D-24) until the Phase 9 dashboard replaces it.
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
]
