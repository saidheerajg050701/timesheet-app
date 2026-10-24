from django.contrib import admin
from django.urls import include, path

from directory.views import admin_login

urlpatterns = [
    path("admin/login/", admin_login),  # one login page for the whole app
    path("admin/", admin.site.urls),
    path("", include("directory.urls")),
    path("", include("timesheets.urls")),
    path("", include("analytics.urls")),
    path("", include("payroll.urls")),
]
